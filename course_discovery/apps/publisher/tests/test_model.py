# pylint: disable=no-member
import ddt
from django.core.urlresolvers import reverse
from django.test import TestCase
from django_fsm import TransitionNotAllowed

from course_discovery.apps.core.tests.factories import UserFactory
from course_discovery.apps.publisher.models import State, Course
from course_discovery.apps.publisher.tests import factories


@ddt.ddt
class CourseRunTests(TestCase):
    """ Tests for the publisher `CourseRun` model. """

    @classmethod
    def setUpClass(cls):
        super(CourseRunTests, cls).setUpClass()
        cls.course_run = factories.CourseRunFactory()

    def test_str(self):
        """ Verify casting an instance to a string returns a string containing the course title and start date. """
        self.assertEqual(
            str(self.course_run),
            '{title}: {date}'.format(
                title=self.course_run.course.title, date=self.course_run.start
            )
        )

    def test_post_back_url(self):
        self.assertEqual(
            self.course_run.post_back_url,
            reverse('publisher:publisher_course_runs_edit', kwargs={'pk': self.course_run.id})
        )

    @ddt.unpack
    @ddt.data(
        (State.DRAFT, State.NEEDS_REVIEW),
        (State.NEEDS_REVIEW, State.NEEDS_FINAL_APPROVAL),
        (State.NEEDS_FINAL_APPROVAL, State.FINALIZED),
        (State.FINALIZED, State.PUBLISHED),
        (State.PUBLISHED, State.DRAFT),
    )
    def test_workflow_change_state(self, source_state, target_state):
        """ Verify that we can change the workflow states according to allowed transition. """
        self.assertEqual(self.course_run.state.name, source_state)
        self.course_run.change_state(target=target_state)
        self.assertEqual(self.course_run.state.name, target_state)

    def test_workflow_change_state_not_allowed(self):
        """ Verify that we can't change the workflow state from `DRAFT` to `PUBLISHED` directly. """
        self.assertEqual(self.course_run.state.name, State.DRAFT)
        with self.assertRaises(TransitionNotAllowed):
            self.course_run.change_state(target=State.PUBLISHED)


class CourseTests(TestCase):
    """ Tests for the publisher `Course` model. """

    def setUp(self):
        super(CourseTests, self).setUp()
        self.course = factories.CourseFactory()
        self.course2 = factories.CourseFactory()

        self.user1 = UserFactory()
        self.user2 = UserFactory()
        self.user3 = UserFactory()
        self.group_a = factories.GroupFactory()
        self.group_b = factories.GroupFactory()
        self.user1.groups.add(self.group_a)
        self.user2.groups.add(self.group_b)

    def test_str(self):
        """ Verify casting an instance to a string returns a string containing the course title. """
        self.assertEqual(str(self.course), self.course.title)

    def test_post_back_url(self):
        self.assertEqual(
            self.course.post_back_url,
            reverse('publisher:publisher_courses_edit', kwargs={'pk': self.course.id})
        )

    def test_assign_permission_by_group(self):
        """ Verify that permission can be assigned using the group. """
        self.assert_user_cannot_view_course(self.user1, self.course)
        self.assert_user_cannot_view_course(self.user2, self.course2)

        self.course.assign_permission_by_group(self.group_a)
        self.course2.assign_permission_by_group(self.group_b)

        self.assert_user_can_view_course(self.user1, self.course)
        self.assert_user_can_view_course(self.user2, self.course2)

        self.assert_user_cannot_view_course(self.user1, self.course2)
        self.assert_user_cannot_view_course(self.user2, self.course)

        self.assertEqual(self.course.group_institution, self.group_a)
        self.assertEqual(self.course2.group_institution, self.group_b)

    def assert_user_cannot_view_course(self, user, course):
        """ Asserts the user can NOT view the course. """
        self.assertFalse(user.has_perm(Course.VIEW_PERMISSION, course))

    def assert_user_can_view_course(self, user, course):
        """ Asserts the user can view the course. """
        self.assertTrue(user.has_perm(Course.VIEW_PERMISSION, course))

    def test_group_institution(self):
        """ Verify the method returns groups permitted to access the course."""
        self.assertEqual(self.course.group_institution, None)
        self.course.assign_permission_by_group(self.group_a)
        self.assertEqual(self.course.group_institution, self.group_a)

    def test_get_group_users_emails(self):
        """ Verify the method returns the email addresses of users who are
        permitted to access the course AND have not disabled email notifications.
        """
        self.user3.groups.add(self.group_a)
        self.course.assign_permission_by_group(self.group_a)
        self.assertListEqual(self.course.get_group_users_emails(), [self.user1.email, self.user3.email])

        # The email addresses of users who have disabled email notifications should NOT be returned.
        factories.UserAttributeFactory(user=self.user1, enable_email_notification=False)
        self.assertListEqual(self.course.get_group_users_emails(), [self.user3.email])

    def test_keywords_data(self):
        """ Verify that the property returns the keywords as comma separated string. """
        self.assertFalse(self.course.keywords_data)
        self.course.keywords.add('abc')
        self.assertEqual(self.course.keywords_data, 'abc')

        self.course.keywords.add('def')
        self.assertIn('abc', self.course.keywords_data)
        self.assertIn('def', self.course.keywords_data)


class SeatTests(TestCase):
    """ Tests for the publisher `Seat` model. """

    def setUp(self):
        super(SeatTests, self).setUp()
        self.seat = factories.SeatFactory()

    def test_str(self):
        """ Verify casting an instance to a string returns a string containing the course title and seat type. """
        self.assertEqual(
            str(self.seat),
            '{course}: {type}'.format(
                course=self.seat.course_run.course.title, type=self.seat.type
            )
        )

    def test_post_back_url(self):
        self.assertEqual(
            self.seat.post_back_url,
            reverse('publisher:publisher_seats_edit', kwargs={'pk': self.seat.id})
        )


class StateTests(TestCase):
    """ Tests for the publisher `State` model. """

    def setUp(self):
        super(StateTests, self).setUp()
        self.state = factories.StateFactory()

    def test_str(self):
        """ Verify casting an instance to a string returns a string containing the current state display name. """
        self.assertEqual(
            str(self.state),
            self.state.get_name_display()
        )


class UserAttributeTests(TestCase):
    """ Tests for the publisher `UserAttribute` model. """

    def setUp(self):
        super(UserAttributeTests, self).setUp()
        self.user_attr = factories.UserAttributeFactory()

    def test_str(self):
        """ Verify casting an instance to a string returns a string containing the user name and
        current enable status. """
        self.assertEqual(
            str(self.user_attr),
            '{user}: {enable_email_notification}'.format(
                user=self.user_attr.user,
                enable_email_notification=self.user_attr.enable_email_notification
            )
        )
