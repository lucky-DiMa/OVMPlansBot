from pymongo import MongoClient
from config import MONGO_AUTH_LINK, MONGO_CLUSTER_NAME

mongo_db = MongoClient(MONGO_AUTH_LINK)[MONGO_CLUSTER_NAME]


if __name__ == '__main__':
    from classes import PlansBotUser
    PlansBotUser.get_by_id(90485996)