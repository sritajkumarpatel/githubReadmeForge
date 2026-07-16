<picture>
  <source media="(prefers-color-scheme: dark)" srcset="assets/readme/brand-dark.svg">
  <img alt="Project visual identity" src="assets/readme/brand-light.svg" width="100%">
</picture>

<p align="center">
  <img src="https://cdn.simpleicons.org/mysql" height="34" alt="MySQL" title="MySQL">
  <img src="https://cdn.simpleicons.org/mongodb" height="34" alt="MongoDB" title="MongoDB">
</p>


# Spring Boot - JPA - Hibernate

![License](https://img.shields.io/github/license/...)
![Language](https://img.shields.io/github/languages/top/...)

***A powerful Spring Boot application empowering users to manage their accounts and interests seamlessly through robust REST APIs.***

---

## The Problem

Managing user data and interests can often become a cumbersome task, resulting in inefficient workflows and subpar user experiences. Whether you're a developer trying to build user-centric applications or an organization aiming to manage user information effectively, the pain points are unmistakable:

- **Data Disorganization**: User accounts and interests are frequently stored in disparate formats, making retrieval, updates, and management a hassle.
- **Complex Workflows**: Without a robust system to streamline user operations, developers resort to convoluted code solutions that are hard to maintain and extend.
- **Integration Barriers**: The varying performance of different databases can lead to compatibility issues, hindering smooth data flow and interaction with applications.

These challenges demand a solution that not only organizes data but also provides seamless interaction among users and their interests.

---

## The Solution

This application leverages the power of Spring Boot along with JPA and Hibernate to provide a structured approach to managing user accounts and interests. By employing RESTful APIs, it ensures that interactions with the underlying database are both efficient and intuitive. 

What sets this application apart is its core flexibility: 

- **Unified Data Access**: With JPA and Hibernate integration, developers can effortlessly perform CRUD operations while ensuring optimal performance across different databases, including H2, MySQL, and MongoDB.
- **Robust API Layer**: The application’s API layer is crafted to handle incoming requests and simplify user interactions, promoting a responsive and user-centric experience.
- **Transaction Management**: By incorporating transaction management best practices, the application ensures data integrity during operations, especially in complex scenarios like transferring funds between accounts.

---

## Key Concepts

| Term               | Definition                                                                 |
|--------------------|---------------------------------------------------------------------------|
| UserAccount        | Represents the user accounts, encapsulating fields such as username, password, and user details. |
| Interest           | Represents interests linked to users, detailing preferences and hobbies.  |
| Appointment        | Defines the structure needed for scheduling and managing appointments.    |
| UserAccountController | Handles incoming API requests related to user management.              |
| BankAccountServiceImpl | Contains business logic for managing user-related transactions.       |

---

## How It Works

### Architecture Diagram
![Architecture Diagram](assets/readme/architecture.svg)

### How It Works — Step-by-Step

1. **Step 1 — User Registration**: An incoming request to `POST /api/users/register-user` triggers the `UserAccountController` which handles user data registration.
2. **Step 2 — Interest Assignment**: Post user creation, the controller enables users to create and associate interests via `POST /api/interests/update/{userID}`.
3. **Step 3 — Data Retrieval**: Users can fetch their account details through a simple `GET /api/users/user/{id}` call, facilitated by the `UserAccountController`.

### Component Table

| Component                                | Role                                           | Input                   | Output                        |
|------------------------------------------|------------------------------------------------|-------------------------|-------------------------------|
| UserAccountController                    | API Controller for user operations            | User registration data  | User account creation response |
| BankAccountServiceImpl                   | Service layer for business logic               | User-related commands   | Processed user and interest data |
| UserAccountSpringDataRepository          | Repository layer handling data access         | CRUD operations on UserAccount | Respective entity retrieval   |

---

## Features

### User Registration and Management
Provides REST APIs for user registration, retrieval, and management, simplifying user account handling and connection with their interests.

### CRUD Operations Using JPA and Hibernate
Facilitates Create, Read, Update, Delete operations on entities using JPA and Hibernate, enabling powerful database interactions with real-time data processing.

### Transaction Management
Handles transaction management for any bank account-related operations, ensuring data integrity during critical processes.

---

## Installation

To set up the application, follow these steps:

1. **Clone the repository**:
   ```shell
   git clone https://github.com/...
   ```
2. **Run the Spring Boot application**:
   ```shell
   ./mvnw spring-boot:run
   ```

---

## Configuration & Parameters

### Environment Variables

<details>
<summary>Click to expand</summary>

| Variable                    | Description                                | Required | Default |
|-----------------------------|--------------------------------------------|----------|---------|
| spring.datasource.url       | The database URL for H2, MySQL, or MongoDB. | Yes      |         |
| spring.datasource.username   | The username for database connections.      | Yes      |         |
| spring.datasource.password   | The password for database connections.      | Yes      |         |

</details>

---

## API Reference

### User Registration API
- **POST** `/api/users/register-user`: Registers a new user account.
  - Example:
    ```shell
    curl -X POST -H "Content-Type: application/json" -d '{"userName": "newuser", "password": "securepass"}' http://localhost:8080/api/users/register-user
    ```

### Retrieve Users API
- **GET** `/api/users/all-users`: Retrieves all registered users.
  
### Interest Management API
- **POST** `/api/interests/update/{userID}`: Creates an interest for the specified user.
- **DELETE** `/api/interests/delete/{interestId}`: Deletes the specified interest.

---

## Data Models

| Field          | Type          | Description                        |
|----------------|---------------|------------------------------------|
| id             | Long          | Unique identifier for the user account. |
| userName       | String        | Username of the user.               |
| password       | String        | Password for user authentication.     |
| age            | Integer       | Age of the user.                     |
| city           | String        | City where the user resides.        |
| country        | String        | Country of the user.                 |
| phoneNumber    | String        | Contact number of the user.          |
| gender         | String        | Gender of the user.                  |

---

## Repository Structure
```plaintext
readme_forge_clone_tob98jx0/
├── .mvn/                      # Maven wrapper files
│   └── wrapper/
│       ├── maven-wrapper.jar
│       └── maven-wrapper.properties
├── src/
│   ├── main/
│   │   ├── java/
│   │   │   └── in/
│   │   │       └── sritaj/      # Main application Java package
│   │   └── resources/
│   │       ├── application.properties  # Configuration file
│   │       ├── data.sql               # Test data for H2 database
│   │       └── db_schema.sql          # Schema for MySQL
├── test-data/                  # Assets for testing
│   └── test.png
├── test-download/              # Download test assets
│   └── test.jpg
├── .gitignore                  # Git ignore file
├── README.md                   # Project documentation
├── mvnw                        # Maven Wrapper executable
├── mvnw.cmd                    # Maven Wrapper executable for Windows
└── pom.xml                    # Maven configuration
```

---

## Contributing & License

We welcome contributions! For detailed guidelines, please refer to [CONTRIBUTING.md](CONTRIBUTING.md). 

This project is licensed under the terms of the [MIT License](LICENSE). Test your implementations using:

```shell
./mvnw test
``` 

Rediscover the way you manage user data with a Spring Boot application that gives you the right tools at your fingertips. Get started today!