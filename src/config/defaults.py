import os

BZM_APIM_DEFAULT_BASE_URL: str = "https://api.runscope.com"
BZM_APIM_BASE_URL: str = os.getenv("BZM_API_TEST_BASE_URL", BZM_APIM_DEFAULT_BASE_URL)
TOOLS_PREFIX: str = "blazemeter_apitest"

ACCOUNTS_ENDPOINT: str = "/account"
TEAMS_ENDPOINT: str = "/teams"
BUCKETS_ENDPOINT: str = "/buckets"
TESTS_ENDPOINT: str = "/buckets/{}/tests"
SCHEDULES_ENDPOINT: str = "/buckets/{}/tests/{}/schedules"
STEPS_ENDPOINT: str = "/buckets/{}/tests/{}/steps"
RESULTS_ENDPOINT: str = "/buckets/{}/tests/{}/results"
BUCKET_LEVEL_RESULTS_ENDPOINT: str = "/buckets/{}/results"
TEST_ENVIRONMENT_ENDPOINT: str = "/buckets/{}/tests/{}/environments"
