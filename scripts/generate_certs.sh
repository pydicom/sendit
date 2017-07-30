# This is needed for certificate on server, interactive run for now
cd /tmp
openssl genrsa -out server.key 4096 && mv server.key /etc/ssl/certs

cp /code/csr_details.txt /tmp
WORKDIR /tmp
echo CN = \"cci-docker-webapp-p03.stanford.edu\" >> csr_details.txt

# call openssl now by piping the newly created file in
openssl req -new -sha256 -nodes -out server.csr -newkey rsa:2048 -keyout server.key -config csr_details.txt
openssl x509 -req -days 365 -in server.csr -signkey server.key -out server.crt

cp server.key /etc/ssl/private
cp server.crt /etc/ssl/certs

# Create the challenge folder in the webroot
mkdir -p /var/www/html/.well-known/acme-challenge/

# Get a signed certificate with acme-tiny
mkdir /opt/acme_tiny
git clone https://github.com/diafygi/acme-tiny
mv acme-tiny /opt/acme-tiny/

service nginx start
python /opt/acme-tiny/acme_tiny.py --account-key /etc/ssl/certs/server.key --csr /etc/ssl/certs/server.csr --acme-dir /var/www/html/.well-known/acme-challenge/ > ./signed.crt

wget -O - https://letsencrypt.org/certs/lets-encrypt-x3-cross-signed.pem > intermediate.pem
cat signed.crt intermediate.pem > chained.pem
mv chained.pem /etc/ssl/certs/

# Reinstall root certificates
apt-get install -y ca-certificates
mkdir /usr/local/share/ca-certificates/cacert.org
wget -P /usr/local/share/ca-certificates/cacert.org http://www.cacert.org/certs/root.crt http://www.cacert.org/certs/class3.crt
update-ca-certificates
