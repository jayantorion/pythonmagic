#!/bin/bash

echo "Testing authentication and API endpoints..."

# Register a new user
echo "1. Registering new user..."
REGISTER_RESPONSE=$(curl -s -X POST http://127.0.0.1:8765/api/v1/auth/register \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser2","password":"testpass123","full_name":"Test User"}')
echo "Register response: $REGISTER_RESPONSE"

# Extract token from response
TOKEN=$(echo $REGISTER_RESPONSE | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
echo "Token: $TOKEN"

if [ -z "$TOKEN" ]; then
  echo "Failed to get token from registration"
  exit 1
fi

# Login to get token (alternative)
echo "2. Logging in..."
LOGIN_RESPONSE=$(curl -s -X POST http://127.0.0.1:8765/api/v1/auth/login/json \
  -H "Content-Type: application/json" \
  -d '{"username":"testuser2","password":"testpass123"}')
echo "Login response: $LOGIN_RESPONSE"

LOGIN_TOKEN=$(echo $LOGIN_RESPONSE | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)
echo "Login token: $LOGIN_TOKEN"

# Use login token for subsequent calls
AUTH_TOKEN=${LOGIN_TOKEN:-$TOKEN}

# Fetch user profile
echo "3. Fetching user profile..."
PROFILE_RESPONSE=$(curl -s -X GET http://127.0.0.1:8765/api/v1/candidate/profile \
  -H "Authorization: Bearer $AUTH_TOKEN")
echo "Profile response: $PROFILE_RESPONSE"

# Fetch user facts
echo "4. Fetching user facts..."
FACTS_RESPONSE=$(curl -s -X GET http://127.0.0.1:8765/api/v1/candidate/facts \
  -H "Authorization: Bearer $AUTH_TOKEN")
echo "Facts response: $FACTS_RESPONSE"

# Fetch user jobs (should be empty initially)
echo "5. Fetching user jobs..."
JOBS_RESPONSE=$(curl -s -X GET http://127.0.0.1:8765/api/v1/jobs \
  -H "Authorization: Bearer $AUTH_TOKEN")
echo "Jobs response: $JOBS_RESPONSE"

# Run job discovery
echo "6. Running job discovery..."
DISCOVER_RESPONSE=$(curl -s -X POST http://127.0.0.1:8765/api/v1/jobs/discover \
  -H "Authorization: Bearer $AUTH_TOKEN")
echo "Discover response: $DISCOVER_RESPONSE"

# Fetch jobs again to see if any were discovered
echo "7. Fetching jobs after discovery..."
JOBS_AFTER_RESPONSE=$(curl -s -X GET http://127.0.0.1:8765/api/v1/jobs \
  -H "Authorization: Bearer $AUTH_TOKEN")
echo "Jobs after discovery: $JOBS_AFTER_RESPONSE"

echo "Testing completed."