from kafka import KafkaProducer
import json
from loguru import logger
from pymongo import MongoClient
import os
import sys

from loguru import logger
    
game_id = os.environ['GAME_ID']
table_id = os.environ['TABLE_ID']
try:
    host = os.environ['HOSTNAME']
except:
    host = 'localhost'

logger.configure(extra={"table_id": table_id, "host": host})
logger.add(sys.stderr,
               format="{extra[host]} - {extra[table_id]} - [{time}] - {message}")




class Emitter:
    '''
    Event Emitter for Virtual Games

    '''

    def __init__(self) -> None:
        self.bootstrap_servers = os.environ['KAFKA_BROKERS']
        self.producer = KafkaProducer(bootstrap_servers=self.bootstrap_servers,
                                      value_serializer=lambda v: json.dumps(v).encode('utf-8'), acks='all')
        self.DB_URL = os.environ['DB_CONNECTION_URL']
        self.DB_NAME = os.environ['DB_DATABASE']
        self.db = MongoClient(self.DB_URL)[self.DB_NAME]
        self.collection = self.db['bets']
        self.RTP_BASE_URL = os.environ['RTP_BASE_URL']
        logger.info(f'KAFKA : {self.bootstrap_servers} - DB : {self.DB_URL}/{self.DB_NAME} - RTP : {self.RTP_BASE_URL}')

    def emit(self, value):
        '''
        Send the event to the Kafka Server
        '''
        round_id = value['result']['roundId']
        event_type = value['result']['eventType']
        table_id = value['result']['tableId']
        logger.info(
            f'Emitting event {event_type} for table {table_id} and round {round_id}')
        future = self.producer.send(topic='game-events-topic',
                                    value=value, key=str.encode(str(round_id)))
        result = future.get(timeout=60)
        logger.info(json.dumps(result))
        self.producer.flush()

    def collect_bets(self, round_key):
        result = self.collection.aggregate([
            {
                '$match': {
                    'round_key': round_key
                }
            }, {
                '$group': {
                    '_id': {
                        'market_type': '$market_type',
                        'bet_details᎐runnerType': '$bet_details.runnerType',
                        'bet_details᎐oddValue': '$bet_details.oddValue'
                    },
                    'SUM(bet_details᎐stakeAmount)': {
                        '$sum': '$bet_details.stakeAmount'
                    }
                }
            }, {
                '$project': {
                    'total_bet_amount': '$SUM(bet_details᎐stakeAmount)',
                    'runnerType': '$_id.bet_details᎐runnerType',
                    'market_type': '$_id.market_type',
                    'oddValue': '$_id.bet_details᎐oddValue',
                    '_id': 0
                }
            }
        ])
        data = list(result)
        return data

    def get_values_from_data(self, market, runner, data):
        filtered_data = [x for x in data if x['runnerType']
                         == runner if x['market_type'] == market]
        if len(filtered_data):
            return filtered_data[0]
        else:
            return {'total_bet_amount': 0, 'oddValue': None, 'runnerType': None, 'market_type': None}