#!/usr/bin/env bash

# Docker Check
PACKAGE="docker-ce"

if dpkg -s $PACKAGE >/dev/null 2>&1; then
    echo "Docker installed. We can continue"
else
    echo -e "Docker is not installed. Please copy-paste the following commands first.\nThen restart the machine (for the usermod rights)"
    echo -e "\e[35msudo apt-get install curl\ncurl -fsSL https://get.docker.com | sh \nsudo usermod -aG docker $USER\e[0m"
    exit 1
fi

# Common variables
TIMEZONE=$(timedatectl show --property=Timezone --value 2>/dev/null)
HOSTNAME=$(hostname)
DEFAULT_TARGET_DIR="$HOME/docker/"
DOMAIN=$(awk '/^search/ {print $NF}' /etc/resolv.conf)

if [ -n "$DOMAIN" ]; then
    FQDN=$HOSTNAME.$DOMAIN
else
    FQDN="$HOSTNAME"
fi

DJANGO_SITE_URL=$FQDN
DJANGO_SECRET_KEY=$(LC_ALL=C tr -dc 'A-Za-z0-9!@#%&*-+' </dev/urandom |head -c 64; echo)

# Default db, user and pass if user is lazy
DEFAULT_DB_NAME="battomatic"
DEFAULT_DB_USER="battomatic"
DEFAULT_DB_PASS="battomatic"

printf "┌────────────────────────┐\n"
printf "| %-22s |\n" "Batt-o-matic installer"
printf "| %-22s |\n" "Server: $FQDN"
printf "| %-22s |\n" "TZ: $TIMEZONE"
printf "└────────────────────────┘\n"
echo
echo "You can Cancel this script anytime with CTRL+D"
echo
read -rp "Docker Target directory or hit enter: [$DEFAULT_TARGET_DIR]: " TARGET_DIR
TARGET_DIR=${TARGET_DIR:-$DEFAULT_TARGET_DIR}
echo
while true; do
    read -rp "Mariadb root password: [DO NOT USE $ on Password!] " DB_ROOT_PASS
    [[ -n "$DB_ROOT_PASS" ]] && break
    echo -e "\e[31mMadiaDB password can't be empty\e[0m"
done
echo
read -rp "Mariadb database name or hit enter = [$DEFAULT_DB_NAME]: " DB_NAME
DB_NAME=${DB_NAME:-$DEFAULT_DB_NAME}
echo
read -rp "Mariadb username or hit enter = [$DEFAULT_DB_USER]: " DB_USER
DB_USER=${DB_USER:-$DEFAULT_DB_USER}
echo
read -rp "Mariadb password or hit enter = [$DEFAULT_DB_PASS]: " DB_PASS
DB_PASS=${DB_PASS:-$DEFAULT_DB_PASS}

# If target dir not given
if [ -z "$TARGET_DIR" ]; then
    echo "Target directory cannot be empty."
    exit 1
fi

TARGET_DIR="${TARGET_DIR/#\~/$HOME}"

# It target dir already exist 
if [ -e "$TARGET_DIR" ]; then
    echo "Directory already exists: $TARGET_DIR I dont' care it's contents!"
    read -rp "Continue and copy files into it? [y/N]: " CONFIRM
    if [[ ! "$CONFIRM" =~ ^[Yy]$ ]]; then
        echo "Cancelled."
        exit 0
    fi
else
    mkdir -p "$TARGET_DIR"
    mkdir -p "$TARGET_DIR"/mariadb
    mkdir -p "$TARGET_DIR"/nginx
fi

TARGET_DIR_ABS="$(realpath "$TARGET_DIR")"

echo -e "\e[35m- Copying project files to: $TARGET_DIR_ABS \e[0m"

cp -a battomatic "$TARGET_DIR_ABS/"
cp -a battomatic_dockerfile "$TARGET_DIR_ABS/"
cp -a README.md "$TARGET_DIR_ABS/"
cp -a LICENSE "$TARGET_DIR_ABS/"

echo -e "\e[35m- Get some running privileges for the scripts \e[0m"

chmod a+x "$TARGET_DIR_ABS/"battomatic/entrypoint.sh
chmod a+x "$TARGET_DIR_ABS/"battomatic/manage.py

echo -e "\e[35m- Generating .env, docker-compose.yml and nginx.conf from template...\e[0m"

export TARGET_DIR_ABS DB_ROOT_PASS TIMEZONE DJANGO_SECRET_KEY DJANGO_SITE_URL DB_NAME DB_PASS DB_USER

envsubst '${DB_ROOT_PASS} ${TIMEZONE} ${DJANGO_SECRET_KEY} ${DJANGO_SITE_URL} ${DB_NAME} ${DB_PASS} ${DB_USER}' < ".env.template" > "$TARGET_DIR_ABS/.env"
envsubst '${TARGET_DIR_ABS}' < "docker-compose.yml.template" > "$TARGET_DIR_ABS/docker-compose.yml"
envsubst '${DJANGO_SITE_URL}' < "nginx.conf.template" > "$TARGET_DIR_ABS/nginx/nginx.conf"

echo -e "\e[35m- Trying to pull and start mariadb, adminer and nginx-proxy...\e[0m"

cd ${TARGET_DIR_ABS}

# Pulling the Docker Containers
for i in {1..3}; do
    if docker compose pull mariadb adminer nginx-proxy; then
        echo -e "\e[35mPull succeeded.\e[0m"
        break
    fi

    echo "Pull failure (round $i/3)."

    if [[ $i -eq 3 ]]; then
        echo -e "\e[31mPull failure 3 times on a row, exiting...\e[0m"
        exit 1
    fi
    sleep 5
done

# Starting the Docker Containers
docker compose up mariadb adminer nginx-proxy -d

sleep 10

echo -e "\e[35m- Let's check if the mariadb is on fire...\e[0m"

# New database and user + flush privileges
SQL="
USE mysql;
CREATE DATABASE IF NOT EXISTS \`$DB_NAME\` CHARACTER SET utf8mb4 COLLATE utf8mb4_general_ci;
CREATE USER IF NOT EXISTS '$DB_USER'@'%' IDENTIFIED BY '$DB_PASS';
GRANT ALL PRIVILEGES ON \`$DB_NAME\`.* TO '$DB_USER'@'%';
FLUSH PRIVILEGES;
"
if docker inspect -f '{{.State.Running}}' mariadb 2>/dev/null | grep -q true; then

    echo -e "\e[35mGood! MariaDB is running. Let's wait for a while and make some DB-Shenanigans then...\e[0m"
    sleep 8
    cd ${TARGET_DIR_ABS}
    
    if docker exec -i mariadb mariadb -u root -h mariadb --password=$DB_ROOT_PASS -Bse "$SQL"
        then
            echo -e "\e[35mDatabase is now set\e[0m"
        else
            exit_code=$?
            echo -e "\e[31mDatabase initializion failed, exit-code: $exit_code \e[0m" >&2
            exit "$exit_code"
    fi   
    
else
    echo
    echo -e "\e[31mCheck with the command\n\n docker compose logs mariadb --follow\n\n What is wrong with mariadb?\e[0m"
    exit 1
fi
echo -e "\e[35m- Let's build the battomatic...\e[0m"

cd ${TARGET_DIR_ABS}
docker compose build batt-o-matic
sleep 2
docker compose up batt-o-matic -d

if docker inspect -f '{{.State.Running}}' batt-o-matic 2>/dev/null | grep -q true; then
    echo  -e "\e[35mIt's alive! Let's make some Migrations first then superuser...\n\nFollow the instructions. This will be the admin account for Battomatic.\e[0m"
    echo
    docker compose exec -it batt-o-matic python manage.py makemigrations
    docker compose exec -it batt-o-matic python manage.py migrate
    docker compose exec -it batt-o-matic python manage.py createsuperuser
    echo    
    echo -e "\e[35mCheck the website for\nhttp://$HOSTNAME:3005/\nhttp://battomatic.$FQDN/\e[0m"
    echo
    echo -e "\e[35mIf all went right, you can login and then add your first battery on the database.\nLook at the values on Battery chemistries table with Admin\nThey are intended to identify a fully charged battery in flight logs.\n\nBTW! You need to add atleast A-record for that battomatic.$FQDN to your router DNS\e[0m"
else
    echo
    echo -e "\e[31m Something came up off the ass of Timo\n\n Check with docker compose logs batt-o-matic --follow\nWhat it is complaining this time...\e[0m"
    exit 1
fi

echo -e  "\e[35mAll Done!\e[0m"