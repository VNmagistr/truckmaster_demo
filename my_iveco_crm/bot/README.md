# Telegram Bot Documentation — TruckMaster

## Table of Contents
1. [Getting Started](#getting-started)
2. [Bot Registration](#bot-registration)
3. [Features for All Users](#features-for-all-users)
4. [Admin Features](#admin-features)
5. [Reminder System](#reminder-system)
6. [FAQ](#faq)

---

## Getting Started

### How to find the bot?
1. Open Telegram
2. Search for the bot by name: **@YourBotName** *(replace with actual name)*
3. Or follow the link: `t.me/YourBotName`

### First launch
Press the **Start** button or send the `/start` command

---

## Bot Registration

On first launch, the bot will ask you to share your phone number for identification.

### Step 1: Provide phone number
1. Press the **"Share phone number"** button
2. Confirm the action in the Telegram dialog

### Step 2: Link to account
- If your phone number exists in the TruckMaster database, the bot will automatically link your account
- You will receive a message confirming successful linking
- A keyboard with available features will appear

> **Important:** If your number is not found in the database, contact the manager for registration.

---

## Features for All Users

After successful authorization, the following features are available:

### My Vehicles

**What it does:** Shows a list of all your vehicles registered in the system.

**How to use:**
1. Press the **"My vehicles"** button
2. The bot will show your vehicle list
3. Tap a vehicle to see its repair history

**Example response:**
```
Your vehicles in our system. Select one to view history:

Iveco Daily (AA1234BB)
Iveco Eurocargo (BC5678HH)
```

**Repair history:**
After selecting a vehicle, you will see:
- Service order numbers
- Work completion dates
- Current order statuses

### Check Order Status

**What it does:** Check the status of a specific service order.

**How to use:**
1. Press the **"Check order status"** button
2. Enter the order number (digits only)
3. Get order information

**Example:**
```
Enter: 12345

Bot response:
Service Order #12345

Client: Your Name
Vehicle: AA1234BB
Status: Done
Created: 15.12.2024
```

---

## Admin Features

Available only to users with **Admin** or **Manager** role.

### All Vehicles

**What it does:** Shows a list of all vehicles in the system (first 20).

**Information:**
- License plate
- Vehicle model
- Owner
- Last 7 digits of VIN

**Example:**
```
All vehicles in the system (first 20):

Iveco Daily (AA1234BB)
   Owner: John Smith
   VIN: ...1234567

Iveco Eurocargo (BC5678HH)
   Owner: Peter Johnson
   VIN: ...7654321
```

### All Orders

**What it does:** Shows the latest 15 orders in the system.

**Information:**
- Order number
- Client
- Vehicle
- Status
- Created date

**Example:**
```
Latest 15 orders:

#12345
   Client: John Smith
   Vehicle: AA1234BB
   Status: Done
   Date: 15.12.2024

#12346
   Client: Peter Johnson
   Vehicle: BC5678HH
   Status: In Progress
   Date: 16.12.2024
```

### Find Vehicle by Plate

**What it does:** Quick vehicle search by license plate.

**How to use:**
1. Press **"Find vehicle by plate"**
2. Enter license plate (full or partial)
3. Get detailed information

**Search example:**
```
Enter: AA1234

Bot response (if 1 vehicle found):
Vehicle found:

Plate: AA1234BB
Model: Iveco Daily
VIN: ...1234567
Owner: John Smith

Recent orders:
  - #12345 - Done (15.12.2024)
  - #12300 - Done (01.12.2024)
```

**If multiple found:**
```
Found 3 vehicles:

Iveco Daily (AA1234BB)
   Owner: John Smith

Iveco Eurocargo (AA1234CC)
   Owner: Mike Williams

Iveco Stralis (AA1234MM)
   Owner: Transport LLC
```

### Find Client

**What it does:** Search for a client by name with full information about them and their vehicles.

**How to use:**
1. Press **"Find client"**
2. Enter name or part of the name
3. Get detailed information

**Search features:**
- Case-insensitive search
- Partial name search supported
- Multiple words search (finds clients matching ALL words)

**Search examples:**

*Example 1: Full name*
```
Enter: John Smith

Response:
Client found:

Name: John Smith Jr.
Phone: +380501234567
Email: jsmith@example.com

Vehicles (2):
  - AA1234BB - Iveco Daily
    VIN: ...1234567
  - BC5678HH - Iveco Eurocargo
    VIN: ...7654321
```

*Example 2: Partial name*
```
Enter: john

Response (if multiple found):
Found 3 clients:

John Smith Jr.
   Phone: +380501234567
   Vehicles: 2

John Williams
   Phone: +380509876543
   Vehicles: 1

Johnson Transport LLC
   Phone: +380441234567
   Vehicles: 5
```

*Example 3: Company search*
```
Enter: LLC transport

Finds all companies with "LLC" AND "transport" in the name
```

**If nothing found:**
```
No client found matching 'xyz'.

Try entering part of the name.
```

### Statistics

**What it does:** Shows overall system statistics.

**Information:**
- Total clients
- Total vehicles
- Total orders
- Bot users count
- Linked users count
- Orders by status breakdown

**Example:**
```
System statistics:

Clients: 245
Vehicles: 312
Orders: 1,847
Bot users: 89
Linked: 76

By status:
  - Done: 1,654
  - In Progress: 143
  - New: 35
  - Canceled: 15
```

---

## Reminder System

The system automatically sends reminders about required vehicle maintenance.

### Reminder Types

#### Scheduled Maintenance
- **When:** If more than 180 days since last service
- **Message includes:**
  - Vehicle plate
  - Model
  - Last service date
  - Days since last service

**Example reminder:**
```
Maintenance Reminder

Vehicle: AA1234BB
Model: Iveco Daily
Last service: 15.06.2024
Days ago: 185

We recommend scheduling a maintenance service!
```

#### Oil Change
- Reminders for engine oil replacement
- Configured individually per vehicle

#### Technical Inspection
- Reminders for upcoming technical inspection
- Sent N days before expiration

#### Custom Reminders
- Configured by manager individually
- Can be about anything (insurance, documents, etc.)

### Reminder Configuration

Reminder settings are managed by the administrator via the web interface.

**Configuration options:**
- Reminder type
- Vehicle
- Days in advance to notify
- Repeat frequency
- Send time

### Delivery Schedule

**Default:** Reminders are sent at **9:00 AM** daily.

**Maintenance check:** System checks maintenance needs every **6 hours**.

---

## FAQ

### The bot doesn't respond to messages

**Solution:**
1. Check your internet connection
2. Try sending `/start`
3. If it still doesn't work, contact technical support

### Can't link phone number

**Causes:**
- Your phone number is not in the database
- Number entered in wrong format

**Solution:**
Contact the manager to add your number to the system.

### Can't see my vehicles

**Causes:**
- Vehicles are not linked to your account
- Account data is not synchronized

**Solution:**
Contact the administrator to verify vehicle assignments.

### Not receiving reminders

**Causes:**
- Reminders are not configured for your vehicles
- Reminders are disabled by administrator
- No service history for the vehicle

**Solution:**
Contact the manager to configure reminders.

### How to change phone number?

**Solution:**
Contact the administrator. Phone number changes are done via the web interface.

### Why can't I see admin features?

**Cause:**
Insufficient access privileges.

**Solution:**
If you need admin access, contact management.

### How to unsubscribe from reminders?

**Solution:**
Contact the manager. Reminders can be disabled via the web interface.

### The bot shows incorrect information

**Solution:**
1. Try restarting the conversation: `/start`
2. If the issue persists, contact technical support with a description of the problem

---

## Technical Support

**For issues, contact:**
- Email: support@example.com
- Phone: +380 (44) 123-45-67
- Working hours: Mon-Fri 9:00-18:00

---

## Tips

### Saving Important Information
If the bot sent important information (order number, service date), you can:
- Pin the message in the chat
- Save to Telegram's "Saved Messages"
- Take a screenshot

### Quick Access
Add the bot to favorites or pin the chat for quick access.

### Group Chats
The bot works only in private messages. Adding the bot to groups is not supported.

---

**Documentation version:** 1.0
**Last updated:** 16.12.2024
