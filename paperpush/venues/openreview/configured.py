"""Configured OpenReview editions; recorded ICLR/AAAI forms stay unchanged."""

from ..configured import ConfiguredVenue
from .main import OpenReviewVenue


class ConfiguredOpenReviewVenue(ConfiguredVenue, OpenReviewVenue):
    login = OpenReviewVenue.login
    is_logged_in = OpenReviewVenue.is_logged_in
