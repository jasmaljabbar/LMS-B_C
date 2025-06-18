- Add a SECRET_KEY for JWT encoding/decoding. Generate a strong, random string (e.g., using ```openssl rand -hex 32```). 
- Insert admin user credentials. 
```
INSERT INTO users (id, username, email, password_hash, user_type, is_active, photo)
VALUES (
    1,
    'admin',
    'admin@example.com',
    '$2b$12$WofojNbsiCmELgmExBz0D.aLla5l3GI9BQwEXjR3FYeBmWxO1O3gO',
    'Admin',
    1,
    ''
);
```


# Cloud Deployment

```shell
cd terraform
terraform init
terraform apply
```


### Get cloud sql database details
```shell
$ terraform output
database_name = "cloudnative_lms"
database_password_secret_id = <sensitive>
database_user_name = "lms_user"
generated_database_password = <sensitive>
instance_connection_name = "ai-powered-lms:us-central1:cloudnative-lms-instance"
instance_name = "cloudnative-lms-instance"
instance_private_ip_address = ""
instance_public_ip_address = "35.194.49.185"
```

## connect to cloud sql db using cloud sql proxy for local access.
```shell
cloud_sql_proxy ai-powered-lms:us-central1:cloudnative-lms-instance --credentials-file /home/rajan/CREDENTIALS/ai-powered-lms-ceef6a835ad5.json
```

### Get Cloud SQL database password using this command
```shell
gcloud secrets versions access latest --secret="cloudnative-lms-instance-db-password" --project="ai-powered-lms"; echo
```

### Connect to mysql database
```shell
mysql -ulms_user -p<DB_PASSWORD> -h127.0.0.1
```
#### Database interactions
```shell
Welcome to the MariaDB monitor.  Commands end with ; or \g.
Your MySQL connection id is 404
Server version: 8.0.40-google (Google)

Copyright (c) 2000, 2018, Oracle, MariaDB Corporation Ab and others.

Type 'help;' or '\h' for help. Type '\c' to clear the current input statement.

MySQL [(none)]> show databases;
+--------------------+
| Database           |
+--------------------+
| cloudnative_lms    |
| information_schema |
| mysql              |
| performance_schema |
| sys                |
+--------------------+
5 rows in set (0.255 sec)

MySQL [(none)]> use cloudnative_lms;
Database changed
MySQL [cloudnative_lms]> show tables;
Empty set (0.252 sec)

MySQL [cloudnative_lms]> exit
Bye
```
