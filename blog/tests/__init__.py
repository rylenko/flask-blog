from betamax import Betamax

from app.config import TestingConfig


with Betamax.configure() as config:
	config.cassette_library_dir = TestingConfig.OAUTH_CASSETTES_DIR
