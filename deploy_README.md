# VideoResearch Deployment & CI/CD

This project uses Flask + SQLAlchemy with AWS RDS (MySQL) in production. We support two deployment modes:

- **Local / dev** (uses SQLite by default)
- **Containerized / prod** (uses MySQL via `DATABASE_URL` on EC2)

We also provide a manual CI/CD “fresh‐start” workflow so you can re‐seed your RDS database on demand without touching data on every code push.

---

## 1. Prerequisites

- Python 3.9+, pip, virtualenv
- Docker & Docker Compose
- AWS CLI & ECR repo (for CI)
- EC2 instance (t3.micro or larger) in same VPC/AZ as your RDS
- RDS MySQL endpoint, credentials
- Git installed on local and EC2 machines

---

## 2. Local Development

1. Clone the repo

   ```bash
   git clone https://github.com/your-org/VideoProject.git
   cd VideoProject/NewPortal
   ```

2. Create and activate a virtual environment

   ```bash
   python -m venv venv
   # On Windows
   venv\Scripts\activate
   # On Linux/Mac
   source venv/bin/activate
   ```

3. Install dependencies

   ```bash
   pip install -r requirements.txt
   ```

4. Initialize the database (SQLite by default)

   ```bash
   flask db upgrade
   # To load sample data
   python load_videos.py
   python translate_categories.py
   python update_video.py
   ```

5. Run the development server

   ```bash
   flask run
   # Or with specific host/port
   flask run --host=0.0.0.0 --port=5000
   ```

6. Access the application at http://localhost:5000

---

## 3. Docker Setup

### Building and Running Locally with Docker

1. Build the Docker image:

   ```bash
   docker build -t videoapp .
   ```

2. Run the container (SQLite mode for local development):
   ```bash
   docker run -p 5000:5000 videoapp
   ```

### Using Docker Compose

1. Create a `.env` file with your environment variables:

   ```
   # For local testing with SQLite (optional)
   # DATABASE_URL=sqlite:////app/instance/mydatabase.db

   # For production with MySQL
   DATABASE_URL=mysql+pymysql://username:password@your-rds-endpoint:3306/dbname
   SECRET_KEY=your-secure-secret-key

   # Set to "true" only for initial setup or database reset
   # RUN_DB_INIT=true
   ```

2. Run with Docker Compose:

   ```bash
   # Normal run (no data initialization)
   docker-compose up -d

   # For first-time setup or DB reset
   RUN_DB_INIT=true docker-compose up -d
   ```

3. To stop services:
   ```bash
   docker-compose down
   ```

---

## 4. EC2 Deployment (Manual)

### First-time Setup

1. Connect to your EC2 instance:

   ```bash
   ssh -i /path/to/your-key.pem ec2-user@your-ec2-ip
   ```

2. Install Docker and Docker Compose on Amazon Linux 2023:

   ```bash
   # Update packages and install Docker
   sudo dnf update -y
   sudo dnf install -y docker
   sudo systemctl enable docker
   sudo systemctl start docker
   sudo usermod -aG docker ec2-user

   # Install Docker Compose v1
   sudo curl -L "https://github.com/docker/compose/releases/download/1.29.2/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
   sudo chmod +x /usr/local/bin/docker-compose
   docker-compose --version
   ```

3. Clone the repository:

   ```bash
   mkdir -p /home/ec2-user/VideoResearch
   cd /home/ec2-user/VideoResearch
   git clone https://github.com/your-org/VideoProject.git .
   # OR if using SSH
   # git clone git@github.com:your-org/VideoProject.git .
   ```

4. Create the `.env` file:

   ```bash
   cat > .env << EOF
   DATABASE_URL=mysql+pymysql://username:password@your-rds-endpoint:3306/dbname
   SECRET_KEY=your-secure-secret-key
   # RUN_DB_INIT=false
   EOF
   ```

5. Initial deployment with DB setup:

   ```bash
   # Make init-db.sh executable
   chmod +x scripts/init-db.sh

   # Build and start with database initialization
   export RUN_DB_INIT=true
   docker-compose build
   docker-compose up -d migrator web
   ```

### Creating a Systemd Service

1. Create a systemd service file:

   ```bash
   sudo vim /etc/systemd/system/videoapp.service
   ```

2. Add the following content:

   ```ini
   [Unit]
   Description=VideoResearch Application
   After=docker.service
   Requires=docker.service

   [Service]
   Type=oneshot
   RemainAfterExit=yes
   WorkingDirectory=/home/ec2-user/VideoResearch
   ExecStart=/usr/local/bin/docker-compose up -d
   ExecStop=/usr/local/bin/docker-compose down
   TimeoutStartSec=0

   [Install]
   WantedBy=multi-user.target
   ```

3. Enable and start the service:

   ```bash
   sudo systemctl enable videoapp
   sudo systemctl start videoapp
   sudo systemctl status videoapp
   ```

4. Check logs:
   ```bash
   sudo journalctl -u videoapp.service
   docker-compose logs -f
   ```

### Updating the Application

1. Pull latest code and restart:
   ```bash
   cd /home/ec2-user/VideoResearch
   git pull
   export RUN_DB_INIT=false
   docker-compose build
   docker-compose up -d migrator web
   ```

---

## 5. CI/CD with GitHub Actions

This project includes two GitHub Actions workflows:

### Standard Deployment (deploy.yml)

- Triggered on push to main branch
- Runs tests, then deploys to EC2
- Does NOT re-seed the database

To configure:

1. Add the following GitHub repository secrets:
   - `EC2_HOST`: Your EC2 instance IP or hostname
   - `EC2_SSH_KEY`: Your private SSH key for connecting to EC2

### Fresh-Start DB Reseed (freshstart.yml)

- Manual trigger only
- Pulls latest code
- Completely re-initializes the database with fresh data

To use this workflow:

1. Go to GitHub Actions tab
2. Select "Fresh-Start DB Reseed" workflow
3. Click "Run workflow"
4. Select the branch to deploy (usually main)

---

## 6. Troubleshooting

### Docker Issues

1. **OCI runtime error** ("executable file not found"):

   - Check that the Dockerfile is named correctly (case-sensitive)
   - Ensure gunicorn is in requirements.txt
   - Make sure scripts/init-db.sh has execute permissions

2. **Database connectivity issues**:

   - Verify DATABASE_URL in .env file
   - Check security group allows traffic from EC2 to RDS
   - Test connection: `docker-compose exec web python -c "from app import db; print(db.engine.connect())"`

3. **Permission denied errors**:
   - Check file ownership: `sudo chown -R ec2-user:ec2-user /home/ec2-user/VideoResearch`
   - Ensure init-db.sh is executable: `chmod +x scripts/init-db.sh`

### Systemd Service Issues

1. **Service fails to start**:

   - Check service status: `sudo systemctl status videoapp`
   - View logs: `sudo journalctl -u videoapp.service`
   - Verify paths in service file match actual Docker and docker-compose installations

2. **Application not accessible**:
   - Check if container is running: `docker ps`
   - Check container logs: `docker-compose logs web`
   - Verify EC2 security group allows traffic on port 5000
   - Test locally on EC2: `curl http://localhost:5000`

---

## 7. Database Management

### Manual Migration Commands

```bash
# Create a new migration
docker-compose exec web flask db migrate -m "Description of changes"

# Apply migrations
docker-compose exec web flask db upgrade

# Rollback to previous version
docker-compose exec web flask db downgrade
```

### Database Backup & Restore

Using AWS RDS snapshots is recommended. Alternatively:

```bash
# Backup MySQL database
docker-compose exec web sh -c 'mysqldump -h $DB_HOST -u $DB_USER -p$DB_PASSWORD $DB_NAME > /app/backup.sql'

# Restore from backup
docker-compose exec web sh -c 'mysql -h $DB_HOST -u $DB_USER -p$DB_PASSWORD $DB_NAME < /app/backup.sql'
```

---

## 8. Monitoring & Maintenance

### Checking Container Status

```bash
docker-compose ps
docker stats
```

### Viewing Logs

```bash
# All logs
docker-compose logs

# Follow logs in real-time
docker-compose logs -f

# View logs for a specific service
docker-compose logs web
```

### Cleaning Up Docker Resources

```bash
# Remove stopped containers
docker-compose rm

# Remove unused images
docker image prune

# Remove all unused resources (use with caution)
docker system prune
```
