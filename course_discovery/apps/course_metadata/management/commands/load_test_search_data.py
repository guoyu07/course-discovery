from datetime import datetime, timedelta

from django.core.management import BaseCommand

from course_discovery.apps.core.models import Partner
from course_discovery.apps.course_metadata.choices import CourseRunStatus, CourseRunPacing, ProgramStatus
from course_discovery.apps.course_metadata.models import Course, CourseRun, Program, ProgramType

MICROMASTER_TYPE = ProgramType.objects.get(name='MicroMasters')
XSERIES_TYPE = ProgramType.objects.get(name='XSeries')
PARTNER = Partner.objects.all().first()

TIMES = [
    ('today', datetime.now()),
    ('plus_three', datetime.now() + timedelta(days=3)),
    ('minus_three', datetime.now() - timedelta(days=3)),
    ('plus_ten', datetime.now() + timedelta(days=10)),
    ('minus_ten', datetime.now() - timedelta(days=10)),
    ('plus_ninety', datetime.now() + timedelta(days=90)),
    ('minus_ninety', datetime.now() - timedelta(days=90)),
    ('plus_365 dogs and cats', datetime.now() + timedelta(days=365)),
    ('minus_365 quick brown fox lazy dog', datetime.now() - timedelta(days=365)),
]


class Command(BaseCommand):
    help = 'Refresh course metadata from external sources.'

    def handle(self, *args, **options):
        self.delete_objects()
        for title, start in TIMES:
            course = self.load_course_run(title, start)
            self.load_course_run(title, start, self_paced=True)
            self.load_micromaster(title, course)
            self.load_xseries(title, course)

    def delete_objects(self):
        Course.objects.all().delete()
        CourseRun.objects.all().delete()
        Program.objects.all().delete()

    def load_course_run(self, title, start, self_paced=False):
        print(title)
        course = Course.objects.create(
            title=title,
            partner=PARTNER,
            key='test/{}{}'.format(title[:8], 'sp' if self_paced else ''),
            full_description="dogs cats foxes living together!"
        )

        CourseRun.objects.create(
            course=course,
            key='test/{}{}/run'.format(title[:8], 'sp' if self_paced else ''),
            status=CourseRunStatus.Published,
            start=start,
            pacing_type=CourseRunPacing.Self if self_paced else CourseRunPacing.Instructor
        )
        return course

    def load_micromaster(self, title, course):
        program = Program.objects.create(
            status=ProgramStatus.Active,
            title='MicroMasters {}'.format(title),
            partner=PARTNER,
            type=MICROMASTER_TYPE
        )
        program.courses.add(course)

    def load_xseries(self, title, course):
        program = Program.objects.create(
            status=ProgramStatus.Active,
            title='XSeries {}'.format(title),
            partner=PARTNER,
            type=XSERIES_TYPE
        )

        program.courses.add(course)
