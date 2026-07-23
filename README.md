# Bank Queuing Simulation 

A simple simulation model of a single-server bank queuing system (M/M/1 queuing model concept). This project simulates customer arrivals, service delays, and queue management to analyze key performance metrics of a bank teller station.

---

##  Features

* **Customer Arrival Simulation:** Generates random or predefined inter-arrival times for incoming bank customers.
* **Service Time Modeling:** Models varying service times spent at the bank teller window.
* **Single-Server Queue Management:** Tracks customers waiting in line when the teller is busy (FIFO - First In, First Out).
* **Performance Metrics Calculation:**
  * Average waiting time per customer
  * Probability of a customer having to wait
  * Total server idle time & utilization percentage
  * Average queue length

---

## How It Works

1. **Arrival:** A customer arrives at the bank. If the server (teller) is free, service begins immediately.
2. **Waiting:** If the server is busy, the customer joins the queue.
3. **Service:** Once the server finishes with the current customer, the next customer in line is served.
4. **Departure:** The customer exits the system, and simulation time logs are updated.

---

##  Getting Started

### Prerequisites

* Specify any prerequisites here (e.g., **Python 3.x**, **C++ Compiler**, or **Java JDK**)

### Installation

1. Clone the repository:
   ```bash
   git clone [https://github.com/RashiBista/Bank-Queuing.git](https://github.com/RashiBista/Bank-Queuing.git)
