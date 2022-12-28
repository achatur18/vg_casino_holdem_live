from emitter import Emitter
import time
import json
import os
from loguru import logger
import requests


class CasinoHoldemLiveEmitter(Emitter):
    '''
    CasinoHoldemLive Events emitter
    '''

    def __init__(self, table_id, game_id) -> None:
        super().__init__()
        self.table_id = table_id
        self.game_type = 'CasinoHoldemLive'
        self.game_id = game_id
        self.round_id = None
        self.ROOT_PATH = (os.sep).join(__file__.split(os.sep)[:-1])

    def get_round_key(self):
        if self.round_id:
            return f'RGONLINE-{self.game_id}-{self.table_id}-{self.round_id}'
        return None

    def get_zerojson(self):
        return json.load(open(f'{self.ROOT_PATH}/zero.json', 'r'))

    def expand_card(self, card):
        suit = card[1]
        rank = card[0]
        if suit == 's':
            suit = 'spades'
        elif suit == 'c':
            suit = 'clubs'
        elif suit == 'h':
            suit = 'hearts'
        else:
            suit = 'diamonds'
        if rank == 'j':
            rank = 'jack'
        elif rank == 'q':
            rank = 'queen'
        elif rank == 'k':
            rank = 'king'
        elif rank == 'a':
            rank = 'ace'
        elif rank == 'x':
            rank = '10'
        return {'suit': suit, 'rank': rank}

    def emit_start(self):
        '''
        Emit the start event 
        '''
        self.round_id = str(self.table_id)+"."+str(int(time.time()))
        current_ts = int(time.time() * 1000)
        event_type = 'ROUND_START'
        value = {"result": {
            "eventType": event_type,
            "gameType": self.game_type,
            "tableId": self.table_id,
            "roundId": self.round_id,
            "ts": current_ts,
            "betTime": current_ts
        }, "sequenceId": current_ts}
        self.emit(value)

    def emit_stop(self):
        '''
        Emit the stop event 
        '''
        current_ts = int(time.time() * 1000)
        event_type = 'NO_MORE_BETS'
        value = {"result": {
            "eventType": event_type,
            "gameType": self.game_type,
            "tableId": self.table_id,
            "roundId": self.round_id,
            "ts": current_ts,
            "betTime": current_ts
        }, "sequenceId": current_ts}
        self.emit(value)

    def get_cards(self):
        round_key = self.get_round_key()
        data = self.collect_bets(round_key)
        bets_json = self.get_zerojson()
        for k in range(len(data)):
            runner = data[k]['runnerType']
            market = data[k]['market_type']
            oddValue = data[k]['oddValue']
            betsamount = data[k]['total_bet_amount']
            for i in range(len(bets_json)):
                if(bets_json[i]['market_type'] == market):
                    for j in range(len(bets_json[i]['runners'])):
                        if(bets_json[i]['runners'][j]['runnerType'] == runner):
                            bets_json[i]['runners'][j]['totalStake'] = betsamount
                            bets_json[i]['runners'][j]['oddValue'] = oddValue

        logger.info(bets_json)
        json_data = {'bet_data': bets_json,
                     'table_id': self.table_id, 'round_id': self.round_id}
        try:
            resp = requests.post(
                f'{self.RTP_BASE_URL}/rtp/casino_holdem_live', data=json.dumps(json_data)).json()
            self.left_card = resp['left_card']
            self.right_card = resp['right_card']
            self.center_card = resp['center_card']
        except Exception as e:
            logger.info(e)

    def emit_left_card(self):
        left_card = self.expand_card(self.left_card)
        logger.info(f'CasinoHoldemLive : {left_card}')
        current_ts = int(time.time() * 1000)
        event_type = 'NEW_CARD'
        value = {"result": {
            "eventType": event_type,
            "gameType": self.game_type,
            "tableId": self.table_id,
            "roundId": self.round_id,
            "ts": current_ts,
            "betTime": current_ts
        }, "sequenceId": current_ts, "playerACards": [left_card]}
        self.emit(value)

    def emit_right_card(self):
        right_card = self.expand_card(self.right_card)
        left_card = self.expand_card(self.left_card)
        logger.info(f'CasinoHoldemLive : {right_card}')
        current_ts = int(time.time() * 1000)
        event_type = 'NEW_CARD'
        value = {"result": {
            "eventType": event_type,
            "gameType": self.game_type,
            "tableId": self.table_id,
            "roundId": self.round_id,
            "ts": current_ts,
            "betTime": current_ts
        }, "sequenceId": current_ts, "playerACards": [left_card], "playerCCards": [right_card], "playerBCards": None}
        self.emit(value)

    def emit_center_card(self):
        right_card = self.expand_card(self.right_card)
        left_card = self.expand_card(self.left_card)
        center_card = self.expand_card(self.center_card)
        logger.info(f'CasinoHoldemLive : {center_card}')
        current_ts = int(time.time() * 1000)
        event_type = 'NEW_CARD'
        value = {"result": {
            "eventType": event_type,
            "gameType": self.game_type,
            "tableId": self.table_id,
            "roundId": self.round_id,
            "ts": current_ts,
            "betTime": current_ts
        }, "sequenceId": current_ts, "playerACards": [left_card], "playerCCards": [right_card], "playerBCards": [center_card]}
        self.emit(value)

    def emit_round_end(self):
        right_card = self.expand_card(self.right_card)
        left_card = self.expand_card(self.left_card)
        center_card = self.expand_card(self.center_card)
        current_ts = int(time.time() * 1000)
        event_type = 'ROUND_END'
        value = {"result": {
            "eventType": event_type,
            "gameType": self.game_type,
            "tableId": self.table_id,
            "roundId": self.round_id,
            "ts": current_ts,
            "betTime": current_ts
        }, "sequenceId": current_ts, "playerACards": [left_card], "playerCCards": [right_card], "playerBCards": [center_card]}
        self.emit(value)


if __name__ == "__main__":
    import time
    import sys
    import os

    game_id = os.environ['GAME_ID']
    table_id = os.environ['TABLE_ID']
    
    try:
        host = os.environ['HOSTNAME']
    except:
        host = 'localhost'
    
    logger.configure(extra={"table_id": table_id, "host": host})
    logger.add(sys.stderr,
                   format="{extra[host]} - {extra[table_id]} - [{time}] - {message}")


    game_id = os.environ['GAME_ID']
    table_id = os.environ['TABLE_ID']
    

    logger.info(f'CasinoHoldemLive GAME ID : {game_id}')
    logger.info(f'CasinoHoldemLive TABLE ID : {table_id}')

    if game_id and table_id:
        emitter = CasinoHoldemLiveEmitter(table_id, game_id)
        while True:
            emitter.emit_start()
            time.sleep(20)
            emitter.emit_stop()
            emitter.get_cards()
            emitter.emit_left_card()
            time.sleep(5)
            emitter.emit_right_card()
            time.sleep(5)
            emitter.emit_center_card()
            time.sleep(5)
            emitter.emit_round_end()
            time.sleep(5)
    else:
        logger.info(f'Invalid or empty table and/or game id')
