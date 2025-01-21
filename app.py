# app.py
from flask import Flask, request, jsonify
import redis
import os
import logging

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Redis connection
redis_host = os.getenv('REDIS_HOST', 'redis')
redis_port = int(os.getenv('REDIS_PORT', 6379))
logger.info(f"Connecting to Redis at {redis_host}:{redis_port}")

redis_client = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)


@app.route('/health', methods=['GET'])
def health_check():
    try:
        logger.debug("Health check endpoint called")
        redis_client.ping()
        return jsonify({'status': 'healthy', 'redis': 'connected'}), 200
    except redis.ConnectionError as e:
        logger.error(f"Redis connection error: {str(e)}")
        return jsonify({'status': 'unhealthy', 'redis': 'disconnected'}), 503


@app.route('/data', methods=['POST'])
def set_data():
    logger.debug("POST /data endpoint called")
    data = request.get_json()
    logger.debug(f"Received data: {data}")

    if not data or 'key' not in data or 'value' not in data:
        logger.error("Invalid request data")
        return jsonify({'error': 'Invalid request. Required fields: key, value'}), 400

    try:
        redis_client.set(data['key'], data['value'])
        logger.info(f"Successfully stored key: {data['key']}")
        return jsonify({'message': 'Data stored successfully'}), 201
    except redis.RedisError as e:
        logger.error(f"Redis error: {str(e)}")
        return jsonify({'error': f'Redis error: {str(e)}'}), 500


@app.route('/data/<key>', methods=['GET'])
def get_data(key):
    logger.debug(f"GET /data/{key} endpoint called")
    try:
        value = redis_client.get(key)
        if value is None:
            logger.debug(f"Key not found: {key}")
            return jsonify({'error': 'Key not found'}), 404
        logger.info(f"Successfully retrieved key: {key}")
        return jsonify({'key': key, 'value': value}), 200
    except redis.RedisError as e:
        logger.error(f"Redis error: {str(e)}")
        return jsonify({'error': f'Redis error: {str(e)}'}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)
