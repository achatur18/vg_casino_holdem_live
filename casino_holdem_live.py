from emitter import Emitter
import time
import json
import os
from loguru import logger
import requests


class CasinoHoldemLiveEmitter(Emitter):
    '''
    Teen Patti Events emitter
    '''

    def __init__(self, table_id, game_id) -> None:
        super().__init__()
        self.table_id = table_id
        self.game_type = 'poker'
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
                f'{self.RTP_BASE_URL}/rtp/casino_holdem', data=json.dumps(json_data)).json()
            self.p1_cards = resp['p1_cards']
            self.p2_cards = resp['p2_cards']
            self.common_cards = resp['common_cards']
        except Exception as e:
            logger.info(e)

    def emit_new_card(self, a_ix, b_ix, c_ix):
        p1_cards = self.p1_cards
        p2_cards = self.p2_cards
        common_cards = self.common_cards
        p1_cards = [self.expand_card(card) for card in p1_cards[:a_ix]]
        p2_cards = [self.expand_card(card) for card in p2_cards[:b_ix]]
        common_cards = [self.expand_card(card) for card in common_cards[:c_ix]]

        logger.info(f'player_A: {p1_cards}')
        logger.info(f'player_B: {p2_cards}')
        logger.info(f'Common: {common_cards}')
        current_ts = int(time.time() * 1000)
        event_type = 'NEW_CARD'
        value = {"result": {
            "eventType": event_type,
            "gameType": self.game_type,
            "tableId": self.table_id,
            "roundId": self.round_id,
            "ts": current_ts,
            "betTime": current_ts
        }, "sequenceId": current_ts, 'playerACards': p1_cards, 'playerBCards': p2_cards, 'playerCCards': common_cards}
        self.emit(value)

    def emit_round_end(self):
        p1_cards = [self.expand_card(card) for card in self.p1_cards]
        p2_cards = [self.expand_card(card) for card in self.p2_cards]
        common_cards = [self.expand_card(card)
                        for card in self.common_cards]
        current_ts = int(time.time() * 1000)
        event_type = 'ROUND_END'
        value = {"result": {
            "eventType": event_type,
            "gameType": self.game_type,
            "tableId": self.table_id,
            "roundId": self.round_id,
            "ts": current_ts,
            "betTime": current_ts
        }, "sequenceId": current_ts, 'playerACards': p1_cards, 'playerBCards': p2_cards, 'playerCCards': common_cards}
        self.emit(value)


if __name__ == "__main__":
    import time

    game_id = os.environ['GAME_ID']
    table_id = os.environ['TABLE_ID']

    logger.info(f'CasinoHoldemLiveEmitter GAME ID : {game_id}')
    logger.info(f'CasinoHoldemLiveEmitter TABLE ID : {table_id}')

    if game_id and table_id:
        emitter = CasinoHoldemLiveEmitter(table_id, game_id)
        while True:
            emitter.emit_start()
            time.sleep(15)
            emitter.emit_stop()
            emitter.get_cards()
            time.sleep(3)
            emitter.emit_new_card(1, 0, 0)
            time.sleep(2)
            emitter.emit_new_card(2, 0, 0)
            time.sleep(2)
            emitter.emit_new_card(2, 1, 0)
            time.sleep(2)
            emitter.emit_new_card(2, 2, 0)
            time.sleep(5)
            emitter.emit_new_card(2, 2, 1)
            time.sleep(2)
            emitter.emit_new_card(2, 2, 2)
            time.sleep(2)
            emitter.emit_new_card(2, 2, 3)
            time.sleep(2)
            emitter.emit_new_card(2, 2, 4)
            time.sleep(2)
            emitter.emit_new_card(2, 2, 5)
            time.sleep(4)
            emitter.emit_round_end()
            time.sleep(6)
    else:
        logger.info(f'Invalid or empty table and/or game id')
