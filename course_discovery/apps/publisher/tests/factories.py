from datetime import datetime

from django.contrib.auth.models import Group

import factory
from factory.fuzzy import FuzzyText, FuzzyChoice, FuzzyDecimal, FuzzyDateTime, FuzzyInteger
from pytz import UTC

from course_discovery.apps.core.models import Currency
from course_discovery.apps.core.tests.factories import UserFactory
from course_discovery.apps.course_metadata.choices import CourseRunPacing
from course_discovery.apps.course_metadata.tests import factories
from course_discovery.apps.ietf_language_tags.models import LanguageTag
from course_discovery.apps.publisher.models import Course, CourseRun, Seat, State, UserAttributes


class StateFactory(factory.DjangoModelFactory):

    class Meta:
        model = State


class CourseFactory(factory.DjangoModelFactory):
    title = FuzzyText(prefix="Test çօմɾʂҽ ")
    short_description = FuzzyText(prefix="Test çօմɾʂҽ short description")
    full_description = FuzzyText(prefix="Test çօմɾʂҽ FULL description")
    number = FuzzyText()
    prerequisites = "prereq 1, prereq 2, prereq 3"
    expected_learnings = "learning 1, learning 2, learning 3"
    syllabus = "week 1:  awesomeness"
    learner_testimonial = "Best course ever!"
    level_type = factory.SubFactory(factories.LevelTypeFactory)

    primary_subject = factory.SubFactory(factories.SubjectFactory)
    secondary_subject = factory.SubFactory(factories.SubjectFactory)
    tertiary_subject = factory.SubFactory(factories.SubjectFactory)

    team_admin = factory.SubFactory(UserFactory)

    class Meta:
        model = Course


class CourseRunFactory(factory.DjangoModelFactory):
    course = factory.SubFactory(CourseFactory)
    state = factory.SubFactory(StateFactory)
    start = FuzzyDateTime(datetime(2014, 1, 1, tzinfo=UTC))
    end = FuzzyDateTime(datetime(2014, 1, 1, tzinfo=UTC)).end_dt
    enrollment_start = FuzzyDateTime(datetime(2014, 1, 1, tzinfo=UTC))
    enrollment_end = FuzzyDateTime(datetime(2014, 1, 1, tzinfo=UTC)).end_dt
    certificate_generation = FuzzyDateTime(datetime(2014, 1, 1, tzinfo=UTC))
    min_effort = FuzzyInteger(1, 10)
    max_effort = FuzzyInteger(10, 20)
    language = factory.Iterator(LanguageTag.objects.all())
    pacing_type = FuzzyChoice([name for name, __ in CourseRunPacing.choices])
    length = FuzzyInteger(1, 10)
    notes = "Testing notes"
    preview_url = FuzzyText(prefix='https://example.com/')

    class Meta:
        model = CourseRun


class SeatFactory(factory.DjangoModelFactory):
    type = FuzzyChoice([name for name, __ in Seat.SEAT_TYPE_CHOICES])
    price = FuzzyDecimal(0.0, 650.0)
    currency = factory.Iterator(Currency.objects.all())
    upgrade_deadline = FuzzyDateTime(datetime(2014, 1, 1, tzinfo=UTC))
    course_run = factory.SubFactory(CourseRunFactory)

    class Meta:
        model = Seat


class GroupFactory(factory.DjangoModelFactory):
    name = FuzzyText(prefix="Test Group ")

    class Meta:
        model = Group


class UserAttributeFactory(factory.DjangoModelFactory):
    user = factory.SubFactory(UserFactory)

    class Meta:
        model = UserAttributes
