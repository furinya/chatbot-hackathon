from datetime import datetime

def save_log(data):

    print({
        "date": str(datetime.now()),
        **data
    })