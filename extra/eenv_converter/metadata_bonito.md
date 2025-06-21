## Metadata

### Jogging (folder jogging_mixed)
- based on paper
  - 2 participants with each: 2x piezo at the ankles, 1x pv at the wrist
  - jogging in a public park (with short walking and standing breaks)
- based on file `meta.yml`
  - nodes powered by powerbanks
  - synchronization via GPS
  - pv model: IXYS KXOB25-05X3F
  - piezo model: Mide S128-J1FR-1808YB
  - early afternoon, spring time, central european city
  - intermittent walking/running
  - participants f(29y), m(29y)
  - sheep0: piezo, left ankle
  - sheep1: solar, left wrist
  - sheep2: piezo, right ankle
  - sheep3: piezo, left ankle
  - sheep4: solar, left wrist
  - sheep5: piezo, right ankle
- based on file `notes`
  - sheep0,1,2 on person 0
  - sheep3,4,5 on person 1
- anwered by Kai
  - Precise Location: H942+CX Berlin
  - Route: https://maps.app.goo.gl/qjWAJeZZfLec4cCE8 (there and back)
- based on timestamps: 
  - Date: May 15 2021

### Stairs (folder data_step)
- based on paper
  - 7 pv embedded into an outdoor stair in front of a lecture hall
  - frequent foot traffic causes intermittent shadowing
- based on video `2020-01-16-105730`
  - Date: 16.01.2020 (from filename; Jan 16 from video)
  - Time: end at 13:19 (at timestamp 02:24) => start at ~10:55; 10:57:30 from filename
  - All nodes on the edge of the 2nd step (going by black strip)
  - Sun low, long shadows of trees moving slowly from right to left
  - People use the stairs (low/medium traffic, walking normally, not lingering)
  - Solid shadow (likely from a building) covers nodes towards the end
    - starts moving in from the right at timestamp 01:36
    - covers the entire black strip by 02:05
    - afterwards refractions from the fence cause minor illumination?
- answered by Kai
  - Precise Location: https://www.openstreetmap.org/directions?from=51.026467%2C13.723217
  - PV Model: (he thinks it was) KXOB25-05X3F-TR
  - Power: Ethernet switch
  - Synchronization: PTP to one GPS reference clock

### Stairs 2 (solar_step_2020_02_06)
- discarded because of too static env (constant cloudy)

### Office (folder office_new)
- based on paper
  - 5 pv mounted on doorframe and walls of an office
  - fluorescent lighting
  - people enter, leave and operate the lights
- based on file `meta.yml`
  - 5 pv nodes deployed across a room and hallway with fluorescent lights
  - pv model: IXYS KX0B25-05X3F
  - sheep0,2,3: room
  - sheep4,5: hallway
- answered by Kai
  - Power: (95% sure) PoE (switch)
  - Synchronization: (95% sure) PTP
- based on timestamps:
  - Date: July 01, 2021

### Cars (folder cars_convoi)
- based on paper
  - 2 cars with each: 3x piezo
  - drive in convoi over a various roads
- based on file `meta.yml` (confirmed by file `nodes`)
  - sheep0: following car, trunk
  - sheep1: leading car
  - sheep2: leading car
  - sheep3: following car, dashboard
  - sheep4: leading car
  - sheep5: following car, windshield
- answered by Kai
  - date: Same as Washer
  - Location: Windischleuba, Dresden (exact location unknown)
  - Piezo model: Mide S128-J1FR-1808YB
  - Cars: (yellow) Opel Corsa, ?? (order unknown?)
- based on timestamps:
  - Date: May 11, 2021

### Washer (folder washing_machine)
- based on paper
  - 5 piezo
  - WPB4700H industrial washing machine (confirmed by pictures / video)
  - washing program with maximum load
- based on file `notes` 
  - all locations from pov of looking at the front of the machine
  - sheep0: top (likely top side of the machine)
  - sheep1: back left (likely back side of the machine; left part viewing 'through' the machine?)
  - sheep2: front left (left part of the front side?)
  - sheep3: right side (right side of the machine)
  - sheep4: door
  - sheep5: back right (likely back side of the machine; right part viewing 'through' the machine?)
- based on photos
  - Date: 11.05.2021 (from filename `IMG_20210511_124937.jpg`) => verified from unix timestamp
  - connected via switch (PoE)
  - one node top left of the front side -> sheep2
  - one node top right of the front side
  - no node on the door!
  - one node top middle of the right side -> sheep3
  - one node (front?) middle of the top side -> sheep0
  - GPS capelet
  - Program: `3 Koch 60` (60° C laundry)
- based on videos `IMG_2070.mov`, `IMG_2071.mov` and `VID_20210511_130513`
  - one node top left of the front side -> sheep2
  - one node on the door
  - one node top middle of the right side -> sheep3
  - one node (front?) middle of the top side -> sheep0
- answered by Kai:
  - Location: 295M+PC Rositz
  - Piezo model: Mide S128-J1FR-1808YB
  - Node location:
    - sheep1 and sheep5 from `notes` confirmed
    - sheep1 and sheep5 very likely at the top part of the backside
  - synchronization: PTP via Ethernet + __MAYBE__ one GPS server

# Dates

## jogging
first timestamp of sheep0: 1621081493000000000
=> May 15 2021, 12:25 (UTC) / 14:25 (CEST)

after processing: 1621081752600000000
=> 12:29 (UTC) / 14:29 (CEST)

with Location in Berlin (alexanderplatz is closest):
https://meteostat.net/de/place/de/berlin?s=10389&t=2021-05-15/2021-05-15
- Cloudy, 16C, slight rain
- rain seems weird for running with exposed electronics
=> probably unreliable; omit weather info

## stairs
first timestamp of sheep1: 1579168049700000000
=> Jan 16 2020, 09:47 (UTC) / 10:47 (CET)
=> fits with video (recording presumably started 10 min later)

after processing: 1579171761700000000
=> 10:49 (UTC) / 11:49 (CET)

https://meteostat.net/de/place/de/dresden?s=10488&t=2020-01-16/2020-01-16
- Sunny, 6C

## office
first timestamp of sheep0: 1625124516000000000
=> july 01 2021, 7:30 (UTC) / 9:30 (CEST)

after processing: 1625124518000000000
=> ~same

location unknown => weather unknown

## cars
first timestamp of sheep0: 1620739581000000000
=> May 11 2021, 13:26 (UTC) / 15:26 (CEST)

after processing: 1620739600000000000
=> 13:27 (UTC) / 15:27 (CEST)

## washer
first timestamp of sheep0: 1620727646900000000
=> May 11 2021, 10:07 (UTC) / 12:07 (CEST)

after processing: 1620727713000000000
=> 10:09 (UTC) / 12:09 (CEST)

### washer_tumbling
after processing: 1620729193200000000
=> 10:33 (UTC) / 12:33 (CEST)

# Remaining
- "stairs" / "data_step" dataset (7 PV-Nodes embedded into an outdoor stair in front of a lecture hall)?
  - In what order (left to right) were the nodes (sheep1 - sheep7)
- "office" / "office_new" dataset (5 PV-Nodes mounted on doorframe and walls of an office)
  - Where was this office?
  - Node layout?
  - Were the nodes exposed to sunlight (through windows)?
- "cars" / "cars_convoi" dataset (3 Piezo-Nodes each in 2 cars that drive in convoi over various roads)
  - Were were the nodes in the leading car?
  - What kind of car was it?
  - Any info about the location / route taken?
  - How were the nodes powered / synchronized?
- "washer" / "washing_machine" (5 Piezo-Nodes on an industrial washing machine)
  - One sheep (sheep4) was visible (in pictures/videos) both on the door and in the upper right corner for the front face of the machine. Where was it during the recording?
  - How were the nodes powered / synchronized?
