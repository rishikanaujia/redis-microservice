# app.py
from flask import Flask, request, jsonify
import redis
import os
import logging
from datetime import datetime

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
        # Add timestamp to the stored data
        storage_data = {
            'value': data['value'],
            'timestamp': datetime.utcnow().isoformat(),
            'ttl': data.get('ttl')  # Optional TTL in seconds
        }

        if data.get('ttl'):
            redis_client.setex(data['key'], int(data['ttl']), str(storage_data))
        else:
            redis_client.set(data['key'], str(storage_data))

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


@app.route('/data/<key>', methods=['DELETE'])
def delete_data(key):
    logger.debug(f"DELETE /data/{key} endpoint called")
    try:
        if redis_client.delete(key) == 0:
            return jsonify({'error': 'Key not found'}), 404
        return jsonify({'message': f'Key {key} deleted successfully'}), 200
    except redis.RedisError as e:
        logger.error(f"Redis error: {str(e)}")
        return jsonify({'error': f'Redis error: {str(e)}'}), 500


@app.route('/data/<key>/ttl', methods=['GET'])
def get_ttl(key):
    logger.debug(f"GET TTL for key: {key}")
    try:
        ttl = redis_client.ttl(key)
        if ttl == -2:  # Key doesn't exist
            return jsonify({'error': 'Key not found'}), 404
        elif ttl == -1:  # Key exists but has no TTL
            return jsonify({'key': key, 'ttl': None}), 200
        return jsonify({'key': key, 'ttl': ttl}), 200
    except redis.RedisError as e:
        logger.error(f"Redis error: {str(e)}")
        return jsonify({'error': f'Redis error: {str(e)}'}), 500


@app.route('/data/<key>/ttl', methods=['PUT'])
def update_ttl(key):
    logger.debug(f"UPDATE TTL for key: {key}")
    data = request.get_json()

    if not data or 'ttl' not in data:
        return jsonify({'error': 'TTL value required'}), 400

    try:
        ttl = int(data['ttl'])
        if not redis_client.exists(key):
            return jsonify({'error': 'Key not found'}), 404

        redis_client.expire(key, ttl)
        return jsonify({'message': f'TTL updated for key {key}'}), 200
    except ValueError:
        return jsonify({'error': 'Invalid TTL value'}), 400
    except redis.RedisError as e:
        logger.error(f"Redis error: {str(e)}")
        return jsonify({'error': f'Redis error: {str(e)}'}), 500


@app.route('/data/keys', methods=['GET'])
def list_keys():
    logger.debug("Listing all keys")
    try:
        pattern = request.args.get('pattern', '*')
        keys = redis_client.keys(pattern)
        return jsonify({'keys': keys}), 200
    except redis.RedisError as e:
        logger.error(f"Redis error: {str(e)}")
        return jsonify({'error': f'Redis error: {str(e)}'}), 500


@app.route('/metrics', methods=['GET'])
def get_metrics():
    logger.debug("Getting Redis metrics")
    try:
        info = redis_client.info()
        metrics = {
            'connected_clients': info['connected_clients'],
            'used_memory': info['used_memory_human'],
            'total_commands_processed': info['total_commands_processed'],
            'uptime_seconds': info['uptime_in_seconds']
        }
        return jsonify(metrics), 200
    except redis.RedisError as e:
        logger.error(f"Redis error: {str(e)}")
        return jsonify({'error': f'Redis error: {str(e)}'}), 500


if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001)