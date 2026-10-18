"""Configured ScholarOne deployments; existing recorded journals stay unchanged."""

from ..configured import ConfiguredVenue
from .main import ScholarOneVenue


class ConfiguredScholarOneVenue(ConfiguredVenue, ScholarOneVenue):
    login = ScholarOneVenue.login
    is_logged_in = ScholarOneVenue.is_logged_in
