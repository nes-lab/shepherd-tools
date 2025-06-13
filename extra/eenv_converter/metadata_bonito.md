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
- remaining questions
  - Which person (0/1) is f(29) and which is m(29)?
  + Precise Location (address / GPS coords): H942+CX Berlin
  - Date of recording (optionally precise time of day) -> timestamp in data
  - Weather (might be able to get that from location + date)
  - Optional: Any more information about the route and when/where breaks where?
    - As far as I remember the route was something like this (and back): https://maps.app.goo.gl/qjWAJeZZfLec4cCE8

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
- remaining questions
  - Precise Location (address / GPS coords) -> https://www.openstreetmap.org/directions?from=51.026467%2C13.723217
  - Node locations (order from left to right)
  - pv model (same as jogging dataset?)
    - No, I think it was the smaller KXOB25-05X3F-TR
  - Setup (power source, synchronization)
    - All recorders connected to PoE Ethernet switch for power and control. Synchronized via PTP to one GPS reference clock.

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
- remaining questions
  - More accurate node layout
  - Location (address / GPS), might be irrelevant
    - I don't remember (Dresden, Brisbane or Berlin)
  - Date
  - Setup (power source, synchronization)
    - 95% sure it was PoE and PTP
  - Did room/hallway have windows? If so:
    - time of day
    - weather (might be able to get that from location + date)

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
- remaining questions
  - ASK MARCO, he was driving the second car
  + Date -> Same as Washer.
  - Location (address / GPS), Route Taken
    - Windischleuba - Dresden, don't remember exactly
  - Node locations in leading car
  + Piezo model -> same as jogging dataset
  - Setup (power source, synchronization)
    -  I don't remember. Probably power banks and GPS
  - Any info about the cars
    - One yellow Opel Corsa, the other I don't remember
  - Any info about speed (typical, top), stops (traffic lights, etc)


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
  - Date: 11.05.2021 (from filename `IMG_20210511_124937.jpg`)
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
- remaining questions
  - Date (is 11.05.2021 correct?)
    - Sounds about right
  - Location (address / GPS) -> 295M+PC Rositz
  - synchronization via GPS? (capelet is visible in photos)
    - Maybe one GPS server. Other nodes PTP via Ethernet.
  - Piezo model (same as jogging dataset?)
    - Yes
  - Is Sheep 4 on the door or the top right of the front side?
    - I don't remember.
  - Are Sheep 1 and 5 (back side) also in the top corners?
    - I don't remember but very likely yes.
  - Is interpretation of `notes` right in regards of viewing 'through' the machine for the back side nodes?
    - I don't remember, but very likely yes, everything is with respect to standing in front of the machine.
