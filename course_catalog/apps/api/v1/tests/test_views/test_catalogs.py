# pylint: disable=redefined-builtin,no-member
import datetime
import urllib

import ddt
from django.contrib.auth import get_user_model
import pytz
import responses
from rest_framework.reverse import reverse
from rest_framework.test import APITestCase

from course_catalog.apps.api.tests.jwt_utils import generate_jwt_header_for_user
from course_catalog.apps.api.v1.tests.test_views.mixins import SerializationMixin, OAuth2Mixin
from course_catalog.apps.catalogs.models import Catalog
from course_catalog.apps.catalogs.tests.factories import CatalogFactory
from course_catalog.apps.core.tests.factories import UserFactory
from course_catalog.apps.core.tests.mixins import ElasticsearchTestMixin
from course_catalog.apps.course_metadata.tests.factories import CourseRunFactory

User = get_user_model()


@ddt.ddt
class CatalogViewSetTests(ElasticsearchTestMixin, SerializationMixin, OAuth2Mixin, APITestCase):
    """ Tests for the catalog resource. """
    catalog_list_url = reverse('api:v1:catalog-list')

    def setUp(self):
        super(CatalogViewSetTests, self).setUp()
        self.user = UserFactory(is_staff=True, is_superuser=True)
        self.client.force_authenticate(self.user)
        self.catalog = CatalogFactory(query='title:abc*')
        enrollment_end = datetime.datetime.now(pytz.UTC) + datetime.timedelta(days=30)
        course_end = datetime.datetime.now(pytz.UTC) + datetime.timedelta(days=60)
        self.course_run = CourseRunFactory(
            enrollment_end=enrollment_end,
            end=course_end,
            course__title='ABC Test Course'
        )
        self.course = self.course_run.course
        self.refresh_index()

    def assert_catalog_created(self, **headers):
        name = 'The Kitchen Sink'
        query = '*.*'
        viewer = UserFactory()
        data = {
            'name': name,
            'query': query,
            'viewers': [viewer.username]
        }

        response = self.client.post(self.catalog_list_url, data, format='json', **headers)
        self.assertEqual(response.status_code, 201)

        catalog = Catalog.objects.latest()
        self.assertDictEqual(response.data, self.serialize_catalog(catalog))
        self.assertEqual(catalog.name, name)
        self.assertEqual(catalog.query, query)
        self.assertListEqual(list(catalog.viewers), [viewer])

    def grant_catalog_permission_to_user(self, user, action, catalog=None):
        """ Grant the user access to view `self.catalog`. """
        catalog = catalog or self.catalog
        perm = '{action}_catalog'.format(action=action)
        user.add_obj_perm(perm, catalog)
        self.assertTrue(user.has_perm('catalogs.' + perm, catalog))

    def test_create_without_authentication(self):
        """ Verify authentication is required when creating, updating, or deleting a catalog. """
        self.client.logout()
        Catalog.objects.all().delete()

        response = self.client.post(self.catalog_list_url, {}, format='json')
        self.assertEqual(response.status_code, 403)
        self.assertEqual(Catalog.objects.count(), 0)

    @ddt.data('put', 'patch', 'delete')
    def test_modify_without_authentication(self, http_method):
        """ Verify authentication is required to modify a catalog. """
        self.client.logout()
        url = reverse('api:v1:catalog-detail', kwargs={'id': self.catalog.id})

        response = getattr(self.client, http_method)(url, {}, format='json')
        self.assertEqual(response.status_code, 403)

    def test_create_with_session_authentication(self):
        """ Verify the endpoint creates a new catalog when the client is authenticated via session authentication. """
        self.assert_catalog_created()

    def test_create_with_jwt_authentication(self):
        """ Verify the endpoint creates a new catalog when the client is authenticated via JWT authentication. """
        self.client.logout()
        self.assert_catalog_created(HTTP_AUTHORIZATION=generate_jwt_header_for_user(self.user))

    @responses.activate
    def test_create_with_oauth2_authentication(self):
        self.client.logout()
        self.mock_user_info_response(self.user)
        self.assert_catalog_created(HTTP_AUTHORIZATION=self.generate_oauth2_token_header(self.user))

    def test_create_with_new_user(self):
        """ Verify that new users are created if the list of viewers includes the usernames of non-existent users. """
        new_viewer_username = 'new-guy'
        existing_viewer = UserFactory()
        viewers = [new_viewer_username, existing_viewer.username]
        data = {
            'name': 'Test Catalog',
            'query': '*:*',
            'viewers': ','.join(viewers)
        }

        # NOTE: We explicitly avoid using the JSON data type so that we properly test string parsing.
        response = self.client.post(self.catalog_list_url, data)
        self.assertEqual(response.status_code, 201)

        catalog = Catalog.objects.latest()
        latest_user = User.objects.latest()
        self.assertEqual(latest_user.username, new_viewer_username)
        self.assertListEqual(list(catalog.viewers), [existing_viewer, latest_user])

    def test_create_with_new_user_error(self):
        """ Verify no users are created if an error occurs while processing a create request. """
        # The missing name and query fields should trigger an error
        data = {
            'viewers': ['new-guy']
        }
        original_user_count = User.objects.count()
        response = self.client.post(self.catalog_list_url, data)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(User.objects.count(), original_user_count)

    def test_courses(self):
        """ Verify the endpoint returns the list of courses contained in the catalog. """
        url = reverse('api:v1:catalog-courses', kwargs={'id': self.catalog.id})
        courses = [self.course]

        # These courses/course runs should not be returned because they are no longer open for enrollment.
        enrollment_end = datetime.datetime.now(pytz.UTC) - datetime.timedelta(days=30)
        CourseRunFactory(enrollment_end=enrollment_end, course__title='ABC Test Course 2')
        CourseRunFactory(enrollment_end=enrollment_end, course=self.course)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertListEqual(response.data['results'], self.serialize_catalog_course(courses, many=True))

    def test_contains(self):
        """ Verify the endpoint returns a filtered list of courses contained in the catalog. """
        course_key = self.course.key
        qs = urllib.parse.urlencode({'course_id': course_key})
        url = '{}?{}'.format(reverse('api:v1:catalog-contains', kwargs={'id': self.catalog.id}), qs)

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, {'courses': {course_key: True}})

    def test_get(self):
        """ Verify the endpoint returns the details for a single catalog. """
        url = reverse('api:v1:catalog-detail', kwargs={'id': self.catalog.id})

        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.data, self.serialize_catalog(self.catalog))

    def test_list(self):
        """ Verify the endpoint returns a list of all catalogs. """
        response = self.client.get(self.catalog_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertListEqual(response.data['results'], self.serialize_catalog(Catalog.objects.all(), many=True))

    def test_destroy(self):
        """ Verify the endpoint deletes a catalog. """
        url = reverse('api:v1:catalog-detail', kwargs={'id': self.catalog.id})

        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)
        self.assertFalse(Catalog.objects.filter(id=self.catalog.id).exists())

    def test_update(self):
        """ Verify the endpoint updates a catalog. """
        url = reverse('api:v1:catalog-detail', kwargs={'id': self.catalog.id})
        name = 'Updated Catalog'
        query = 'so-not-real'

        data = {
            'name': name,
            'query': query
        }

        response = self.client.put(url, data, format='json')
        self.assertEqual(response.status_code, 200)

        catalog = Catalog.objects.get(id=self.catalog.id)
        self.assertEqual(catalog.name, name)
        self.assertEqual(catalog.query, query)

    def test_partial_update(self):
        """ Verify the endpoint supports partially updating a catalog's fields. """
        url = reverse('api:v1:catalog-detail', kwargs={'id': self.catalog.id})
        name = 'Updated Catalog'
        query = self.catalog.query
        data = {
            'name': name
        }

        response = self.client.patch(url, data, format='json')
        self.assertEqual(response.status_code, 200)

        catalog = Catalog.objects.get(id=self.catalog.id)
        self.assertEqual(catalog.name, name)
        self.assertEqual(catalog.query, query)

    def test_retrieve_permissions(self):
        """ Verify only users with the correct permissions can create, read, or modify a Catalog. """
        # Use an unprivileged user
        user = UserFactory(is_staff=False, is_superuser=False)
        self.client.force_authenticate(user)
        url = reverse('api:v1:catalog-detail', kwargs={'id': self.catalog.id})

        # A user with no permissions should NOT be able to view a Catalog.
        self.assertFalse(user.has_perm('catalogs.view_catalog', self.catalog))
        response = self.client.get(url)
        self.assertEqual(response.status_code, 403)

        # The permitted user should be able to view the Catalog.
        self.grant_catalog_permission_to_user(user, 'view')
        response = self.client.get(url)
        self.assertEqual(response.status_code, 200)

    def test_list_permissions(self):
        """ Verify only catalogs accessible to the user are returned in the list view. """
        user = UserFactory(is_staff=False, is_superuser=False)
        self.client.force_authenticate(user)

        # An user with no permissions should not see any catalogs
        response = self.client.get(self.catalog_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertListEqual(response.data['results'], [])

        # The client should be able to see permissions for which it has access
        self.grant_catalog_permission_to_user(user, 'view')
        response = self.client.get(self.catalog_list_url)
        self.assertEqual(response.status_code, 200)
        self.assertListEqual(response.data['results'], self.serialize_catalog([self.catalog], many=True))

    def test_write_permissions(self):
        """ Verify only authorized users can update or delete Catalogs. """
        url = reverse('api:v1:catalog-detail', kwargs={'id': self.catalog.id})
        user = UserFactory(is_staff=False, is_superuser=False)
        self.client.force_authenticate(user)

        # Unprivileged users cannot modify Catalogs
        response = self.client.put(url)
        self.assertEqual(response.status_code, 403)
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 403)

        # With the right permissions, the user can perform the specified actions
        self.grant_catalog_permission_to_user(user, 'change')
        response = self.client.patch(url, {'query': '*:*'})
        self.assertEqual(response.status_code, 200)

        self.grant_catalog_permission_to_user(user, 'delete')
        response = self.client.delete(url)
        self.assertEqual(response.status_code, 204)

    def test_username_filter_as_non_staff_user(self):
        """ Verify HTTP 403 is returned when a non-staff user attempts to filter the Catalog list by username. """
        user = UserFactory(is_staff=False, is_superuser=False)
        self.client.force_authenticate(user)

        response = self.client.get(self.catalog_list_url + '?username=jack')
        self.assertEqual(response.status_code, 403)
        expected = {'detail': 'Only staff users are permitted to filter by username. Remove the username parameter.'}
        self.assertDictEqual(response.data, expected)

    def test_username_filter_as_staff_user(self):
        """ Verify a list of Catalogs accessible by the given user is returned when filtering by username as a
        staff user. """
        user = UserFactory(is_staff=False, is_superuser=False)
        catalog = CatalogFactory()

        path = '{root}?username={username}'.format(root=self.catalog_list_url, username=user.username)
        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        self.assertListEqual(response.data['results'], [])

        self.grant_catalog_permission_to_user(user, 'view', catalog)

        response = self.client.get(path)
        self.assertEqual(response.status_code, 200)
        self.assertListEqual(response.data['results'], self.serialize_catalog([catalog], many=True))

    def test_username_filter_as_staff_user_with_invalid_username(self):
        """ Verify HTTP 404 is returned if the given username does not correspond to an actual user. """
        username = 'jack'
        path = '{root}?username={username}'.format(root=self.catalog_list_url, username=username)
        response = self.client.get(path)
        self.assertEqual(response.status_code, 404)
        expected = {'detail': 'No user with the username [{username}] exists.'.format(username=username)}
        self.assertDictEqual(response.data, expected)
