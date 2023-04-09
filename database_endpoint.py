from flask import Flask, request, g
from flask_restful import Resource, Api
from sqlalchemy import create_engine, select, MetaData, Table
from flask import jsonify
import json
import eth_account
import algosdk
from sqlalchemy.orm import sessionmaker
from sqlalchemy.orm import scoped_session
from sqlalchemy.orm import load_only

from models import Base, Order, Log

engine = create_engine('sqlite:///orders.db')
Base.metadata.bind = engine
DBSession = sessionmaker(bind=engine)

app = Flask(__name__)


# These decorators allow you to use g.session to access the database inside the request code
@app.before_request
def create_session():
    g.session = scoped_session(
        DBSession)  # g is an "application global" https://flask.palletsprojects.com/en/1.1.x/api/#application-globals


@app.teardown_appcontext
def shutdown_session(response_or_exc):
    g.session.commit()
    g.session.remove()


"""
-------- Helper methods (feel free to add your own!) -------
"""


def log_message(d):
    # Takes input dictionary d and writes it to the Log table
    message=d
    log_obj = Log(message=Log['message'])
    g.session.add(log_obj)
    g.session.commit()
    pass


"""
---------------- Endpoints ----------------
"""


@app.route('/trade', methods=['POST'])
def trade():
    if request.method == "POST":
        content = request.get_json(silent=True)
        print(f"content = {json.dumps(content)}")
        columns = ["sender_pk", "receiver_pk", "buy_currency", "sell_currency", "buy_amount", "sell_amount", "platform"]
        fields = ["sig", "payload"]
        error = False
        for field in fields:
            if not field in content.keys():
                print(f"{field} not received by Trade")
                print(json.dumps(content))
                log_message(content)
                return jsonify(False)

        error = False
        for column in columns:
            if not column in content['payload'].keys():
                print(f"{column} not received by Trade")
                error = True
        if error:
            print(json.dumps(content))
            log_message(content)
            return jsonify(False)

        # Your code here
        json_string = json.dumps(content)
        contentPyth = json.loads(json_string)

        signature = contentPyth['sig']
        payload = json.dumps(contentPyth['payload'])
        sender_pk = contentPyth['payload']['sender_pk']
        receiver_pk = contentPyth['payload']['reiceiver_pk']
        buy_currency = contentPyth['payload']['buy_currency']
        sell_currency = contentPyth['payload']['sell_currency']
        buy_amount = contentPyth['payload']['buy_amount']
        sell_amount = contentPyth['payload']['sell_amount']
        platform=contentPyth['payload']['platform']
        pk=sender_pk
    
        verification_result=False

        if platform == 'Ethereum':
            eth_encoded_msg = eth_account.messages.encode_defunct(text=payload)
            if eth_account.Account.recover_message(eth_encoded_msg, signature=signature) == pk:
                verification_result = True

        elif platform == 'Algorand':
            if algosdk.util.verify_bytes(payload.encode('utf-8'), signature, pk):
                verification_result = True
        
        if verification_result==True:
            order = {}
            order['sender_pk'] = sender_pk
            order['receiver_pk'] = receiver_pk
            order['buy_currency'] = buy_currency
            order['sell_currency'] = sell_currency
            order['buy_amount'] = buy_amount
            order['sell_amount'] = sell_amount

            # Insert the order
            order_obj = Order(sender_pk=order['sender_pk'], receiver_pk=order['receiver_pk'],
                              buy_currency=order['buy_currency'], sell_currency=order['sell_currency'],
                              buy_amount=order['buy_amount'], sell_amount=order['sell_amount'])

            g.session.add(order_obj)
            g.session.commit()
        else:
            log_message(payload)
        # Note that you can access the database session using g.session


@app.route('/order_book')
def order_book():
    # Your code here
    keyList = ['sender_pk', 'receiver_pk', 'buy_currency', 'sell_currency','buy_amount', 'sell_amount', 'signature']
    query = g.session.query(Order)
    query_result = g.session.execute(query)
    initial_result=[]
    for order in query_result.scalars().all():
        order_dict = dict.fromkeys(keyList)
        order_dict['sender_pk']=order.sender_pk
        order_dict['receiver_pk']=order.receiver_pk
        order_dict['buy_currency'] = order.buy_currency
        order_dict['sell_currency'] = order.sell_currency
        order_dict['buy_amount'] = order.buy_amount
        order_dict['sell_amount'] = order.sell_amount
        order_dict['signature'] = order.signature
        initial_result.append(order_dict)

    # Note that you can access the database session using g.session
    keyList2 = ['data']
    result = dict.fromkeys(keyList2)
    result['data'] = initial_result
    print(result)
    print(jsonify(result))
    return jsonify(result)


if __name__ == '__main__':
    app.run(port='5002')
    
