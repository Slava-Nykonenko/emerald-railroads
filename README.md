![Logo of the project](ER-logo.png)

# Emerald Railroads
> API service for booking train tickets written on DRF.

Emerald Railroads is a scalable backend service built using 
Django Rest Framework (DRF) designed for managing a railway system, 
including stations, routes, journeys, crew, trains, and user ticket 
ordering.

The architecture emphasizes performance through optimized database 
querying (annotations, prefetching) and security using role-based 
access control (Admin, Authenticated User, Anonymous).

### Key Features

* **Custom User Model:** Uses email for authentication (leveraging JWT).
* **Transactional Integrity:** Guarantees atomic creation of orders and 
tickets to prevent data loss.
* **Concurrency Protection:** Implements transactional logic to prevent seat 
double-bookings.
* **Performance:** Utilizes DRF's built-in features for efficient list 
filtering and detail view data loading. 
* **Image Upload:** Dedicated endpoint for secure image uploads to train 
models (Admin-only).

## Installing / Getting started

### Prerequisites

Ensure you have the following installed on your system:
* Python (3.10+)
* Docker (Recommended for development setup)
* Git

#### Clone the repository:
```shell
  git clone https://github.com/Slava-Nykonenko/emerald-railroads.git
  cd emerald-railroads
  python -m venv venv
```
#### For Windows:
```shell
  venv\Scripts\activate
```
#### For Mac/Linux:
```shell
  source venv/bin/activate
```
```shell
  pip install -r requirements.txt
  set DB_HOST=<your db hostname>
  set DB_NAME=<your db name>
  set DB_USER=<your db username>
  set DB_PASSWORD=<your db user password>
  set SECRET_KEY=<your secret key>
  python manage.py migrate
  python manage.py runserver
```

#### Run with Docker
Docker should be installed.

```shell
  docker-compose build
  docker-compose up
```
#### DockerHub Image

You can pull the prebuilt image directly from DockerHub:

```shell
  docker pull slavanykonenko/emerald-railroads-app:latest
```
### Demo Access

For quick testing, you can use the following default user:
- Email: ```user@example.ie```
- Password: ```user-password```

Use these credentials to obtain a JWT token via /api/user/token/ and explore the API endpoints in Swagger UI or Redoc.

Example request:
```
POST /api/user/token/
{
  "email": "user@example.ie",
  "password": "user-password"
}
```
Response:
```
{
  "access": "<access-token>",
  "refresh": "<refresh-token>"
}
```
To make authenticated requests, include the Access Token in the Authorization 
header:
> Authorization: Bearer <your-access-token>

### Initial Configuration

* Create a superuser:
```shell 
  python manage.py createsuperuser
```
* Create a user with /api/user/create/ (optional)
* Get token pair via /api/user/token/
* To refresh an access token use /api/user/token/refresh/
* To retrieve or update the authenticated user's profile go to /api/user/me/

## Developing

Development prioritizes Test-Driven Development (TDD) and security. Ensure all 
business logic, especially transactional integrity for orders and concurrency 
protection for seats, is covered by tests. Optimize database performance by 
using Django's .select_related() and .prefetch_related() strategically to 
prevent N+1 queries. All contributions must adhere to PEP 8 standards 
(enforced by Flake8) and strictly use atomic transactions to guarantee data 
consistency.

### Running tests

The test suite covers model validation, serializer logic, performance 
optimizations, and security permissions.

Run tests from the root directory using Django's test runner:

```shell
  docker-compose exec app python manage.py test
```
### Documentation and Schema

This project uses DRF Spectacular to automatically generate an OpenAPI 3.0 
(Swagger) schema.

**Raw Schema:**  
http://127.0.0.1:8000/api/schema/

**Swagger UI:**<br>
View the interactive API documentation at: 
http://127.0.0.1:8000/api/doc/swagger/

**Redoc:**<br>
View the clean, reference-style documentation at: 
http://127.0.0.1:8000/api/doc/redoc/

### Deploying / Publishing

The Deploying/Publishing stage is the final step where the tested, 
containerized application is moved to a production server for public access. 
This typically involves using Docker Compose (or Kubernetes) to manage the 
service, ensuring a robust and scalable environment. Critical steps include 
configuring a reverse proxy (like Nginx or Caddy) to handle static file 
serving, load balancing, and mandatory SSL/TLS encryption (HTTPS) for 
security. Database migrations are applied, and the deployment process must 
ensure zero downtime by updating containers atomically. Finally, the service 
is monitored using tools that track performance metrics, error rates, and 
security vulnerabilities to ensure continuous operational health.

## Links

- Repository: https://github.com/Slava-Nykonenko/emerald-railroads
- In case of sensitive bugs like security vulnerabilities, please contact
slava.nykon@gmail.com directly. We value your effort to improve the security 
and privacy of this project!
- Related projects:
  - https://github.com/Slava-Nykonenko/skyway-airlines

## Author
Viacheslav Nykonenko<br>
[slava.nykon@gmail.com](mailto:slava.nykon@gmail.com)<br>
[GitHub](https://github.com/Slava-Nykonenko) |
[DockerHub](https://hub.docker.com/repositories/slavanykonenko) |
[LinkedIn](https://www.linkedin.com/in/viacheslav-nykonenko-49211b316/)<br>
+353 85 222 1534 <br>
Carlow, Ireland

## Licensing
The code in this project is licensed under [MIT license](LICENSE.txt).
