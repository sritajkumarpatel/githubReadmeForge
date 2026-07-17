<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/readme/brand-dark.svg">
  <img alt="Project visual identity" src="assets/readme/brand-light.svg" width="100%">
</picture>

<p align="center">
  <img src="https://cdn.simpleicons.org/mysql" height="34" alt="MySQL" title="MySQL">
  <img src="https://cdn.simpleicons.org/mongodb" height="34" alt="MongoDB" title="MongoDB">
</p>


<p align="center">
  <img alt="Concise architecture flow" src="assets/readme/architecture.svg" width="100%">
</p>

# Spring Boot - JPA - Hibernate
![License](https://img.shields.io/github/license/in/sritaj/spring-boot-jpa-hibernate)
![Language](https://img.shields.io/github/languages/top/in/sritaj/spring-boot-jpa-hibernate)

***Unleashing the power of JPA and Hibernate in a robust Spring Boot application.***

---

## The Problem
In today's fast-paced digital world, managing user accounts and appointments in web applications can become an overwhelming challenge. Users often find themselves navigating complex systems where CRUD (Create, Read, Update, Delete) operations are inconsistent, and relationships between multiple entities can quickly spiral into chaos. Frustration arises when:

- Implementing CRUD operations requires excessive boilerplate code and time.
- Poorly structured relationships between user accounts and appointments lead to data challenges.
- Ensuring reliable data storage across various database systems can create integration nightmares.
  
These pain points not only hinder productivity but can also frustrate users seeking a seamless experience.

## The Solution
Our Spring Boot application emerges as a beacon of efficiency amid these challenges. By providing a robust set of RESTful APIs, this application simplifies the management of user accounts and appointments, all while utilizing Spring’s JPA for seamless database interactions with Hibernate for Object-Relational Mapping (ORM). 

What sets this project apart from traditional solutions is its ability to leverage the flexibility of multiple database systems (H2, MySQL, and MongoDB) without sacrificing performance or reliability. With a focus on simplicity and power, our application allows developers to effortlessly integrate, manage, and execute data transactions, leaving them free to innovate without being bogged down by mundane operations.

---

## Key Concepts
| Term | Definition |
| --- | --- |
| UserAccount | Represents a user's account information and associated interests. |
| Appointment | Represents a doctor's appointment, encapsulating relevant details for effective management. |
| BankAccount | Holds information regarding bank accounts, including the balance and owner details. |
| Spring Data REST | Provides RESTful access to the Spring Data repositories, enabling seamless data management. |

---

## How It Works

### Architecture Diagram
![Architecture Diagram](assets/readme/architecture.svg)

### How It Works — Step-by-Step
1. **Step 1 — User Registration**: The process begins at the `UserAccountController` when a client sends a POST request to `/api/users/register-user`, which invokes the `registerUser` method.
2. **Step 2 — Data Persistence**: The `UserAccountSpringDataRepository` is called to persist user data in the designated database, orchestrated by Hibernate.
3. **Step 3 — Appointment Management**: Clients can then manage appointments via `/api/appointments`, triggering methods within the `AppointmentSpringDataRepository` for CRUD operations on `Appointment` entities.

---

## Features

### User Registration and Management
This feature empowers users to easily register and manage their accounts, complete with personal details and interests. 

### Appointment Scheduling
The application supports the management of doctor appointment scheduling through comprehensive CRUD operations. This ensures that patients can easily create, read, update, and cancel appointments.

### Transactional Operations
Handling fund transfers between bank accounts is facilitated through this feature, guaranteeing transactional integrity and efficient data managing processes across various entities.

---

## Installation
1. Clone the repository:
   ```shell
   git clone https://github.com/in/sritaj/spring-boot-jpa-hibernate
   ```
2. Install the dependencies and build the project:
   ```shell
   mvn clean install
   ```
3. Run the Spring Boot application:
   ```shell
   ./mvnw spring-boot:run
   ```

---

## Configuration & Parameters
<details>
<summary>Environment Variables</summary>

| Variable                     | Description                              | Required | Default                   |
| ---------------------------- | ---------------------------------------- | -------- | ------------------------- |
| spring.datasource.url        | The database connection URL              | Yes      | jdbc:h2:mem:testdb       |
| spring.datasource.username    | The database username                      | Yes      | sa                        |
| spring.datasource.password    | The database password                      | Yes      |                           |
| spring.jpa.hibernate.ddl-auto | The strategy for schema generation       | Yes      | update                    |

</details>

---

## API Reference
- **POST** `/api/users/register-user`: Registers a new user account.
- **GET** `/api/users/all-users`: Retrieves a list of all user accounts.
- **GET** `/api/users/user/{id}`: Finds users with matching age, city, and country for a specified user ID.
- **POST** `/api/interests/update/{userID}`: Creates a new interest associated with a user.
- **DELETE** `/api/interests/delete/{interestId}`: Deletes a specific interest based on ID.

### Example using curl

To register a new user:

```bash
curl -X POST http://localhost:8080/api/users/register-user \
-H "Content-Type: application/json" \
-d '{"userName":"john_doe","password":"securePassword","age":30,"city":"New York","country":"USA","phoneNumber":"1234567890","gender":"Male"}'
```

---

## Data Models
| Field          | Type        | Description                                      |
| -------------- | ----------- | ------------------------------------------------ |
| id             | Long        | Unique identifier for the UserAccount entity.   |
| userName       | String      | Username of the user.                            |
| password       | String      | Encrypted password of the user.                 |
| age            | Integer     | Age of the user.                                |
| city           | String      | City where the user resides.                    |
| country        | String      | Country where the user resides.                 |
| appointmentTime| Date        | Scheduled time for the appointment.             |
| patient        | UserAccount | The user who has the appointment.               |
| doctor         | String      | Doctor assigned for the appointment.            |

---

## Repository Structure
```plaintext
readme_forge_clone_nwsexgcw/
├── .mvn/                            # Maven wrapper files
│   └── wrapper/                     # Maven wrapper configuration
│       ├── maven-wrapper.jar        # Jar file for Maven wrapper
│       └── maven-wrapper.properties  # Properties for Maven wrapper
├── src/                             # Source code
│   ├── main/                        # Main application resources
│   │   ├── java/                    # Java code
│   │   │   └── in/                  # Main package
│   │   │       └── sritaj/          # Project-specific code
│   │   └── resources/               # Resource files including config
│   │       ├── application.properties # Configs for the application
│   │       ├── data.sql             # Seed data for H2 in-memory db
│   │       ├── db_schema.sql        # SQL schema for MySQL
│   │       ├── ehcache.xml          # Cache configuration file
│   │       └── table.sql            # Table creation scripts
│   └── test/                        # Test resources
│       └── java/                    # Tests for the application
│           └── in/                  # Test package
│               └── sritaj/          # Specific test implementations
├── .gitignore                       # Git ignore rules
├── README.md                        # Project README
├── mvnw                             # Maven wrapper shell script
├── mvnw.cmd                         # Maven wrapper Windows script
└── pom.xml                          # Maven project configuration
```

---

## Contributing & License
We welcome contributions! Please see the [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines. This project is licensed under the terms of the [MIT License](LICENSE).