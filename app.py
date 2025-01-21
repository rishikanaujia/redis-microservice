# app.py
from flask import Flask, request, jsonify
import redis
import os

app = Flask(__name__)

# Redis connection
redis_host = os.getenv('REDIS_HOST', 'redis')
redis_port = int(os.getenv('REDIS_PORT', 6379))
redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)


@app.route('/health', methods=['GET'])
def health_check():
    try:
        redis_client.ping()
        return jsonify({'status': 'healthy', 'redis': 'connected'}), 200
    except redis.ConnectionError:
        return jsonify({'status': 'unhealthy', 'redis': 'disconnected'}), 503


@app.route('/data', methods=['POST'])
def set_data():
    data = request.get_json()
    if not data or 'key' not in data or 'value' not in data:
        return jsonify({'error': 'Invalid request. Required fields: key, value'}), 400

    try:
        redis_client.set(data['key'], data['value'])
        return jsonify({'message': 'Data stored successfully'}), 201
    except redis.RedisError as e:
        return jsonify({'error': f'Redis error: {str(e)}'}), 500


@app.route('/data/<key>', methods=['GET'])
def get_data(key):
    try:
        value = redis_client.get(key)
        if value is None:
            return jsonify({'error': 'Key not found'}), 404
        return jsonify({'key': key, 'value': value}), 200
    except redis.RedisError as e:
        return jsonify({'error': f'Redis error: {str(e)}'}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)