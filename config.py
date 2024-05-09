from dotenv import dotenv_values


secret_config_dict = dict(dotenv_values(".env.secret"))
shared_config_dict = dict(dotenv_values(".env.shared"))
TEST = bool(int(shared_config_dict["TEST"]))
TOKEN = secret_config_dict[f"{'TEST_' if TEST else ''}TOKEN"]
BASE_WEBHOOK_URL = secret_config_dict["BASE_WEBHOOK_URL"]
MONGO_AUTH_LINK = secret_config_dict["MONGO_AUTH_LINK"]
BY_WEBHOOK = bool(int(shared_config_dict["BY_WEBHOOK"]))  # 0 = False, any other eq True
HOLIDAYS = bool(int(shared_config_dict["HOLIDAYS"]))  # 0 = False, any other eq True
MONGO_CLUSTER_NAME = shared_config_dict[f"{'TEST_' if TEST else ''}MONGO_CLUSTER_NAME"]
SITE_URL = secret_config_dict[f"{'TEST_' if TEST else ''}SITE_URL"]
