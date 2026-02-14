from flask import Flask,jsonify
from task_runner import  run_task
app=Flask(__name__)
@app.route("/run",methods=["GET"])
def run():
	return jsonify(run_task())
@app.route("/ping",methods=["GET"])
def ping():
	return jsonify({"message":"agents pong"})
if __name__=="__main__":
	app.run(host="0.0.0.0",port=8123)
