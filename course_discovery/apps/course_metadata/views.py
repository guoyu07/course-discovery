from django.contrib import messages
from django.core.urlresolvers import reverse
from django.http import HttpResponseRedirect, Http404
from django.utils.translation import ugettext_lazy as _
from django.views.generic import TemplateView, UpdateView

from course_discovery.apps.course_metadata.forms import CourseRunSelectionForm
from course_discovery.apps.course_metadata.models import Program


class QueryPreviewView(TemplateView):
    template_name = 'demo/query_preview.html'


class SearchDemoView(TemplateView):
    template_name = 'demo/search.html'


# pylint: disable=attribute-defined-outside-init
class CourseRunSelectionAdmin(UpdateView):
    """ Create Course View."""
    model = Program
    template_name = 'metadata/admin/course_run.html'
    form_class = CourseRunSelectionForm

    def get_context_data(self, **kwargs):
        if self.request.user.is_authenticated() and self.request.user.is_staff:
            context = super(CourseRunSelectionAdmin, self).get_context_data(**kwargs)
            context.update({
                'program_id': self.object.id,
                'title': _('Change program excluded course runs')
            })
            return context
        raise Http404

    def form_valid(self, form):
        self.object = form.save()
        message = 'The program course runs was changed successfully.'
        messages.add_message(self.request, messages.SUCCESS, message)
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse('admin:course_metadata_program_change', args=(self.object.id,))
