import pickle


credentials = {"fantasypros_cred": {"league_1": {"username": "whitneyjb5","team_id": "11","password": "999jbw","token": "reiHrx0n5o7YstOIFsZ5Gj29UVuuC80z"},"league_2": {"username": "whitneyjb5","team_id": "11","password": "999jbw","token": "reiHrx0n5o7YstOIFsZ5Gj29UVuuC80z"}}, "ftp_cred": {"username": "whitneyjb5","password": "999jbw","domain": "joel-whitney.com"}}


pickle.dump(credentials, open("credentials.p", "wb"))
