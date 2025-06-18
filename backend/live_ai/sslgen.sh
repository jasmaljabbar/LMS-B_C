#!/bin/bash -x
# 1. Generate a private key
openssl genpkey -algorithm RSA -out key.pem -pkeyopt rsa_keygen_bits:2048

# 2. Generate a Certificate Signing Request (CSR) - Fill in details when prompted
#    For Common Name (CN), use 'localhost' if testing locally
openssl req -new -key key.pem -out csr.pem -subj "/CN=localhost"

# 3. Generate the self-signed certificate (valid for 365 days)
openssl x509 -req -days 365 -in csr.pem -signkey key.pem -out cert.pem

# You now have cert.pem (certificate) and key.pem (private key)
# Place these files where the script can access them.
#
