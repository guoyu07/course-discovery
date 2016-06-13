""" Core models. """

from django.contrib.auth.models import AbstractUser
from django.db import models
from django.utils.translation import ugettext_lazy as _
from guardian.mixins import GuardianUserMixin


class User(GuardianUserMixin, AbstractUser):
    """Custom user model for use with OpenID Connect."""
    full_name = models.CharField(_('Full Name'), max_length=255, blank=True, null=True)
    referral_tracking_id = models.CharField(_('Referral Tracking ID'), max_length=255, default='affiliate_partner')

    @property
    def access_token(self):
        """ Returns an OAuth2 access token for this user, if one exists; otherwise None.

        Assumes user has authenticated at least once with edX Open ID Connect.
        """
        social_auth = self.social_auth.first()  # pylint: disable=no-member

        if social_auth:
            return social_auth.access_token

        return None

    class Meta(object):  # pylint:disable=missing-docstring
        get_latest_by = 'date_joined'

    def get_full_name(self):
        return self.full_name or super(User, self).get_full_name()


class UserThrottleRate(models.Model):
    """Model for configuring a rate limit per-user."""

    user = models.ForeignKey(User)
    rate = models.CharField(
        max_length=50,
        help_text=_(
            'The rate of requests to limit this user to. The format is specified by Django'
            ' Rest Framework (see http://www.django-rest-framework.org/api-guide/throttling/).')
    )


class Currency(models.Model):
    """ Table of currencies as defined by ISO-4217. """
    code = models.CharField(max_length=6, primary_key=True, unique=True)
    name = models.CharField(max_length=255)

    def __str__(self):
        return '{code} - {name}'.format(code=self.code, name=self.name)

    class Meta(object):
        verbose_name_plural = 'Currencies'
