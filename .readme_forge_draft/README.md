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

![License](https://img.shields.io/github/license/owner/repo)
![Language](https://img.shields.io/github/languages/top/owner/repo)

***An all-encompassing Spring Boot application demonstrating the power of JPA and Hibernate in managing user accounts and interactions.***

---

## The Problem

In today's digital era, managing user data is not just a technical challenge but a fundamental requirement for businesses. CRM systems, appointment scheduling, and engagement tracking have become the lifelines of modern enterprises. However, the complexity of these tasks can lead to significant pain points for developers and users alike. 

- **Fragmented Systems**: Developers often juggle multiple solutions without creating a unified user management system.
- **Data Management Dilemmas**: Handling user data across different databases increases complexity and could lead to data integrity issues.
- **Scalability Concerns**: As user bases grow, maintaining a responsive application that can handle interactions seamlessly becomes a daunting task.

This project addresses these headaches, offering a sophisticated yet simplified approach to managing user accounts and their interactions.

## The Solution

This application provides a systematic way to streamline user account management by utilizing JPA and Hibernate, allowing for seamless database interactions and robust data handling. With a RESTful API architecture, developers can easily integrate and manipulate user data, regardless of whether it resides in H2, MySQL, or MongoDB.

What differentiates this application is its holistic approach: instead of treating user accounts in isolation, it integrates related functionalities, like appointment scheduling and interest tracking, into a cohesive system. This not only enhances the development experience but also improves user engagement by providing personalized features.

## Key Concepts

| Term                    | Definition |
|-------------------------|------------|
| UserAccount             | Represents a user account in the system with personal and contact details. |
| Appointment             | Defines the characteristics and structure of an appointment linked to a user. |
| Interest                | Specifies user interests, enhancing user engagement and personalization. |
| UserAccountController    | The API gateway that handles requests related to user accounts and directs them to relevant services. |
| BankAccountService      | Contains the business logic for managing bank account operations. |

---

## How It Works

![Architecture Diagram](assets/readme/architecture.svg)

### How It Works — Step-by-Step

1. **Step 1 — User Registration**: The process begins when a user sends a registration request to the `UserAccountController.java`, which utilizes methods from `UserAccountSpringDataRepository.java` to perform CRUD operations on user accounts.
   
2. **Step 2 — Appointment Scheduling**: Upon user registration, the `AppointmentSpringDataRepository.java` is called to create appointment entries linked to the new user's profile.
   
3. **Step 3 — Interest Management**: As users engage with the system, they can update or add interests via the API, which again interacts with `InterestSpringDataRepository.java` to manage these entries effectively.

### Component Table

| Component                          | Role                                  | Input          | Output                       |
|------------------------------------|---------------------------------------|----------------|------------------------------|
| UserAccountController              | Handles API requests for user accounts | User data      | Confirmation message         |
| BankAccountServiceImpl             | Implements bank account logic         | Account data   | Updated account details      |
| UserAccountSpringDataRepository    | Manages user data retrieval           | User ID        | User account entity          |
| AppointmentSpringDataRepository     | Manages appointment entries           | Appointment data| Created appointment entity   |
| InterestSpringDataRepository       | Manages user interests                | Interest data  | Updated interest entry       |

---

## Features

### User Registration and Management
Facilitates the registration and management of user accounts through REST APIs, ensuring users can be easily added and retrieved.

### Appointment Scheduling
Users can book and manage appointments while tracking their statuses using JPA for effective database management.

### Interest Tracking for Users
Allows users to set and manage interests linked to their profiles, enhancing user engagement and personalization.

---

## Installation

To set up the application, follow these commands:

1. Clone the repository:
   ```shell
   $ git clone https://github.com/...
   ```
2. Install the required dependencies:
   ```shell
   $ mvn install
   ```
3. Run the Spring Boot application:
   ```shell
   $ mvn spring-boot:run
   ```

---

## Configuration & Parameters

<details>
<summary>View Configuration Variables</summary>

| Variable                     | Description                                  | Required | Default                    |
|------------------------------|----------------------------------------------|----------|----------------------------|
| spring.datasource.url        | Database connection URL for the application  | Yes      | jdbc:h2:mem:testdb       |
| spring.datasource.username    | Username for connecting to the database      | Yes      | sa                         |
| spring.datasource.password    | Password for connecting to the database      | Yes      |                            |

</details>

<details>
<summary>View CLI Flags</summary>

| Flag                  | Short | Description                                  | Default  |
|-----------------------|-------|----------------------------------------------|----------|
| --server.port         | -p    | Port on which the application will run       | 8080     |
| --spring.profiles.active | -P    | Active profile for loading environment configs| default   |

</details>

---

## API Reference

### User Registration

- **POST** `/api/users/register-user`: Registers a new user with the provided user details.

```shell
curl -X POST http://localhost:8080/api/users/register-user -d '{"username":"john","password":"pass"}'
```

### Retrieve Users

- **GET** `/api/users/all-users`: Retrieves a list of all registered users.

### Update Interest

- **POST** `/api/interests/update/{userID}`: Creates an interest entry for a specified user.

### Delete Interest

- **DELETE** `/api/interests/delete/{interestId}`: Deletes a specified interest by ID.

### Find User

- **GET** `/api/users/user/{id}`: Finds users matching the specified criteria based on a given user ID.

---

## Data Models

| Field         | Type   | Description                                     |
|---------------|--------|-------------------------------------------------|
| id            | Long   | Unique identifier for the user account         |
| userName      | String | User's name                                    |
| password      | String | User's password                                |
| age           | Integer| User's age                                     |
| city          | String | User's city of residence                        |
| country       | String | User's country of residence                     |
| phoneNumber   | String | User's phone number                            |
| gender        | String | User's gender                                   |
| likes         | String | User's interests (brief description)           |
| dislikes      | String | User's dislikes (brief description)            |
| about         | String | About the user (biographical details)           |
| profileUrl    | String | URL to the user's profile picture               |
| hobbies       | String | User-defined hobbies                            |
| appointmentTime| String | Scheduled time for the appointment              |
| started       | Boolean| Indicator if the appointment has started       |
| ended         | Boolean| Indicator if the appointment has ended         |
| reason        | String | Reason for the appointment                      |
| patient       | String | The patient associated with the appointment     |
| doctor        | String | The doctor associated with the appointment      |

---

## Repository Structure

```
readme_forge_clone_icos09h_/
├── .mvn/                         # Maven wrapper files
│   └── wrapper/
│       ├── maven-wrapper.jar     # Maven wrapper jar
│       └── maven-wrapper.properties # Maven wrapper properties
├── src/                          # Source files
│   ├── main/                     # Main application source files
│   │   ├── java/                 # Java files
│   │   │   └── in/               # Package containing project's Java code
│   │   │       └── sritaj/       #
│   │   └── resources/            # Resources used by the application
│   │       ├── application.properties # Configuration properties
│   │       ├── data.sql            # Initialization data for databases
│   │       ├── db_schema.sql       # Database schema
│   │       ├── ehcache.xml         # Caching configuration
│   │       ├── storedprocedures.sql # SQL for stored procedures
│   │       └── table.sql           # SQL table creation scripts
│   └── test/                     # Test source files
│       └── java/                 # Java test files
│           └── in/               #
│               └── sritaj/       #
├── test-data/                   # Sample images for tests
│   └── test.png                   #
├── test-download/                # Downloaded test images
│   └── test.jpg                   #
├── .gitignore                    # Git ignore file
├── README.md                     # Project documentation
├── mvnw                          # Maven wrapper for Unix-based systems
├── mvnw.cmd                      # Maven wrapper for Windows
└── pom.xml                       # Maven configuration file
```

---

## Contributing & License

Contributions are welcome! Please see the [CONTRIBUTING.md](CONTRIBUTING.md) guidelines for details.

This project is licensed under the terms of the MIT license. See the [LICENSE](LICENSE) for more information. 

Test coverage can be verified by running:

```shell
$ mvn test
```