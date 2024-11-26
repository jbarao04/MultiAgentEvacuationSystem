import random
import time

# Room class to represent each room in the building
class Room:
    def __init__(self, floor_number, i,j):
        self.name = f"Room {floor_number}{i}{j}"  # Room ID, e.g., "Room_1"
        self.connections = []  # Rooms connected to this one
        self.elevator_connections = []
        self.staircase_connections = []
        self.coordinates=[floor_number,i,j]
        self.light=True
        self.floor=floor_number
        self.is_on_fire = False
        self.is_damaged = False
        self.is_taken = False
        self.noted_fire=False
        self.noted_earthquake = False
        self.noted_attack = False
        self.begin=0
        self.end=0

    # Method to add a connection to another room
    def add_connection(self, other_room):
        self.connections.append(other_room)
    
    def add_elevator_connection(self, other_room):
        self.elevator_connections.append(other_room)
    
    def add_staircase_connection(self, other_room):
        self.staircase_connections.append(other_room)
    
    def distance_to(self, other_room):
        return abs(self.coordinates[0] - other_room.coordinates[0]) + abs(self.coordinates[1] - other_room.coordinates[1]) + abs(self.coordinates[2] - other_room.coordinates[2])
    
    def get_neighbors(self):
        return self.connections

    def start_fire(self):
        self.is_on_fire = True
        self.spread_fire()
        
    def spread_fire(self):
        if random.random() < 0.1: # There is 10% probability the fire will spread to closer rooms
            next_room=random.choice(self.connections)
            next_room.start_fire()
            print(f"Fire is spreading to {next_room.name}")

    def damage_by_earthquake(self):
        if random.random()<0.5:
            self.light=False
        self.is_damaged = True
    
    def taken_by_attacker(self):
        self.is_taken = True


# Floor class to represent each floor with rooms and assembly points
class Floor:
    def __init__(self, floor_number, num_rows, num_cols):
        self.floor_number = floor_number
        self.rooms = [[Room(floor_number,i,j) for j in range(num_cols)] for i in range(num_rows)]
        self.num_rows=num_rows
        self.num_cols=num_cols

    # Get room by its coordinates on the floor
    def get_room(self, row, col):
        return self.rooms[row][col]

    # Method to create connections between adjacent rooms
    def create_room_connections(self):
        rows, cols = len(self.rooms), len(self.rooms[0])
        for i in range(rows):
            for j in range(cols):
                room = self.get_room(i,j)
                # Connect with room to the right
                if j < cols - 1:
                    right_room = self.rooms[i][j + 1]
                    room.add_connection(right_room)
                    right_room.add_connection(room)
                # Connect with room below
                if i < rows - 1:
                    below_room = self.rooms[i + 1][j]
                    room.add_connection(below_room)
                    below_room.add_connection(room)


class Building:
    def __init__(self):
        # Randomly determine the number of floors, rows (height), and columns (width)
        num_floors = random.randint(1, 6)  # Number of floors between 2 and 6
        self.floors = []
        self.elevator = "Elevator"  # Simplified elevator as a connection between floors
        self.updates=[]
        self.agents = {}
        self.emergency_agents = {}
        self.management_agents = {}
        self.assembly_points = []
        self.num_fires = [0, 0]
        self.num_earthquakes = [0, 0]
        self.num_attacks = [0, 0]
        self.times=[]
        self.agent_times=[]
        self.responses = 0
        self.num_floors=num_floors
        self.rows = random.randint(2, 6)  # Random height between 2 and 6
        self.cols = random.randint(2, 6)   # Random width between 2 and 6
        # Create random floors
        for floor_num in range(1, num_floors + 1):
            self.floors.append(Floor(floor_num, self.rows, self.cols))
            
        print(f"Building created! {num_floors+1} floors and {self.rows}x{self.cols} structure!")
        
        time.sleep(1)
        self.create_floor_connections()

        # Randomly choose two assembly points on the ground floor (first floor)
        self.assembly_points = [
            self.floors[0].get_room(0, 0),  # Top-left corner of first floor
            self.floors[0].get_room(self.floors[0].num_rows - 1, 0)  # Bottom-left corner of first floor
        ]
        
        self.begin = time.time()
        
    # Create room connections within each floor
    def create_floor_connections(self):
        for floor in self.floors:
            floor.create_room_connections()

    def get_room(self, floor, row, col):
        return self.floors[floor].get_room(row, col)

    def get_floor(self, floor_number):
        return self.floors[floor_number - 1]
        
    def add_update(self, update_message):
        # If the updates list already contains 5 updates, remove the oldest one
        if len(self.updates) >= 5:
            self.updates.pop(0)  # Remove the oldest update (first element)
        update_message+="\n"
        # Add the new update message
        self.updates.append(update_message)

    # Connect a room on one floor to a room on another floor via the elevator
    def connect_elevator(self, floor1_room, floor2_room):
        floor1_room.add_elevator_connection(floor2_room)
        floor2_room.add_elevator_connection(floor1_room)
        self.floors[floor2_room.coordinates[0] - 1].elevator = floor2_room
        self.floors[floor1_room.coordinates[0] - 1].elevator = floor1_room

    # Connect a room on one floor to a room on another floor via the staircase
    def connect_staircase(self, floor1_room, floor2_room):
        floor1_room.add_staircase_connection(floor2_room)
        floor2_room.add_staircase_connection(floor1_room)
        self.floors[floor2_room.coordinates[0] - 1].staircase = floor2_room
        self.floors[floor1_room.coordinates[0] - 1].staircase = floor1_room

    def add_agent(self, agent):
        self.agent = agent
        self.agents[self.agent.jid] = self.agent

    def add_emergency_agent(self, emergency_agent):
        self.emergency_agent = emergency_agent
        self.emergency_agents[self.emergency_agent.jid] = self.emergency_agent

    def add_management_agent(self, management_agent):
        self.management_agent = management_agent
        self.management_agents[self.management_agent.jid] = self.management_agent

    def trigger_random_event(self):
        # Randomly trigger a fire or earthquake
        if random.random() < 0.07:  # 7% chance for fire
            floor = random.choice(self.floors)
            room = random.choice(random.choice(floor.rooms))
            room.start_fire()

        if random.random() < 0.05:  # 5% chance for earthquake
            floor = random.choice(self.floors)
            room = random.choice(random.choice(floor.rooms))
            room.damage_by_earthquake()  

        if random.random() < 0.05:  # 5% chance for attack
            floor = random.choice(self.floors)
            room = random.choice(random.choice(floor.rooms))
            room.taken_by_attacker()

    def simulate_step(self):
        self.trigger_random_event()

    def is_building_evacuated(self):
        for i in self.agents.values():
            if i.is_evacuated == False:
                return False
        return True

    def get_random_room(self):
        floor = random.choice(self.floors)
        return random.choice(random.choice(floor.rooms))

    def connect_elevators(self):
        # Connect elevators on the same room position (row, col) for each floor
        col = random.randint(0, min(self.floors[0].num_cols, 5) - 1)  # Random column
        row = random.randint(0, min(self.floors[0].num_rows, 5) - 1)  # Random row
        
        # Go through each pair of consecutive floors and connect the rooms in the same position
        for i in range(len(self.floors) - 1):  # Iterate through floors
            floor1 = self.floors[i]
            floor2 = self.floors[i + 1]

            # Get the room in the same (row, col) for both floors
            room1 = floor1.get_room(row, col)
            room2 = floor2.get_room(row, col)
            
            self.connect_elevator(room1, room2)

    def connect_staircases(self):
        # Connect staircases on the same room position (row, col) for each floor
        col = random.randint(0, min(self.floors[0].num_cols, 5) - 1)  # Random column
        row = random.randint(0, min(self.floors[0].num_rows, 5) - 1)  # Random row
        
        # Go through each pair of consecutive floors and connect the rooms in the same position
        for i in range(len(self.floors) - 1):  # Iterate through floors
            floor1 = self.floors[i]
            floor2 = self.floors[i + 1]

            # Get the room in the same (row, col) for both floors
            room1 = floor1.get_room(row, col)
            room2 = floor2.get_room(row, col)
            
            self.connect_staircase(room1, room2)

    def performance_metrics(self):
        values=[self.num_fires[0],self.num_fires[1],self.num_earthquakes[0],self.num_earthquakes[1],self.num_attacks[0],self.num_attacks[1],len(self.agents.keys()),len(self.agents.keys()),len(self.times)]
        print(f"Number of Fires Extinguished / Total Fires: {self.num_fires[0]}/{self.num_fires[1]}")
        print(f"Number of Earthquakes: {self.num_earthquakes[0]}/{self.num_earthquakes[1]}")
        print(f"Number of Attacks Controlled / Total Attacks: {self.num_attacks[0]}/{self.num_attacks[1]}")
        print(f"Number of Occupant Agents Evacuated / Total Occupant Agents: {len(self.agents.keys())}/{len(self.agents.keys())}")
        
        time_spent_list = []
        for i in self.agents.values():
            time_spent = i.finish_time - self.begin
            time_spent_list.append(time_spent)
            print(f"Agent {i.agent_name} took {time_spent:.2f} to evacuate")
        
        total_time = max(time_spent_list)
        values.append(total_time)
        print(f"Total Evacuation Time: {total_time:.2f}")
        print(f"Number of problems solved by Emergency Responders: {len(self.times)}")
        print(f"Average Response Time of Emergency Responders: {sum(self.times)/len(self.times) if len(self.times) !=0 else 0:.2f}")
        avg_response=sum(self.times)/len(self.times) if len(self.times) !=0 else 0
        values.append(avg_response)
        return values
        
    def update_perf_metrics():
    	return [self.num_fires[0],self.num_fires[1],self.num_earthquakes[0],self.num_earthquakes[1],self.num_attacks[0],self.num_attacks[1]]
