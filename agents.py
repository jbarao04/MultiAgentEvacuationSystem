import spade
from spade.behaviour import CyclicBehaviour, OneShotBehaviour
from spade.message import Message
import asyncio
import time


class OccupantAgent(spade.agent.Agent):
    def __init__(self, jid, password, agent_name, environment, mobility):
        super().__init__(jid, password)
        self.agent_name = agent_name
        self.mobility = mobility
        self.environment = environment
        self.location = environment.get_random_room()
        self.avoid_rooms = set()  # Keep track of rooms to avoid due to fire or earthquake
        self.is_evacuated = False

    async def setup(self):
        update=f"Occupant Agent {self.agent_name} is ready. Location: {self.location.name}, Mobility: {self.mobility}"
        self.environment.add_update(update)
        print(update)
        if self.mobility=="able-bodied": self.pace=4
        else: self.pace=5
        self.add_behaviour(self.ReceiveInstructionsBehaviour())

    class ReceiveInstructionsBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=0.1)
            if msg:
                if msg.body.startswith("Due to"):
                    room_name = msg.body.split()[-1]  # Extract room name to avoid
                    self.agent.avoid_rooms.add(room_name)

                elif msg.body.startswith("Assembly Point"):
                    update=f"{self.agent.agent_name} will redirect his route due to assembly point blocked"
                    self.agent.environment.add_update(update)
                    print(update)
                    await self.redirect_route_to_exit()

                elif msg.body == "EVACUATE":
                    await self.navigate_to_exit()
                    
                elif msg.body == "ELEVATOR ACCESS GRANTED":
                    return
                    
        async def elevator_request(self):
            agents = self.agent.environment.management_agents.keys()
            update=f"{self.agent.agent_name} requested Elevator"
            self.agent.environment.add_update(update)
            print(update)
            for agent in agents:
                msg = Message(to=str(agent))
                msg.body = f"Send Elevator to Room"
                await self.send(msg)
        
        '''
        
        # Optimal Algorithm
        
        def get_next_room_towards_exit(self, target_room):
            neighbors = self.agent.location.get_neighbors()

            # Filter out rooms to avoid (due to fire or earthquake)
            neighbors = [room for room in neighbors if room.name not in self.agent.avoid_rooms]
            if not neighbors:
                update = f"No available rooms to move towards! {self.agent.agent_name} is stuck."
                self.agent.environment.add_update(update)
                print(update)
                return None

            # Initialize emergency responder locations
            responder_locations = [responder.location for responder in self.agent.environment.emergency_agents.values()]

            # Helper function to calculate if the room has adjacent hazard rooms
            def has_adjacent_hazards(room):
                return any(
                    neighbor.is_on_fire or neighbor.is_damaged
                    for neighbor in room.get_neighbors()
                )

            # Score each neighbor based on the criteria
            def calculate_score(room):
                # Distance to target room (lower is better)
                distance_to_exit = room.distance_to(target_room)

                # Distance to the nearest responder (higher is better for safety)
                distance_to_responder = min(
                    (room.distance_to(responder_location) for responder_location in responder_locations),
                    default=float('inf')  # No responders nearby
                )

                # Hazard proximity penalty (adjacent hazard rooms are less safe)
                hazard_penalty = 3 if has_adjacent_hazards(room) else 0

                # Weighted score: Adjust weights as needed
                score = (distance_to_exit * 2) + (distance_to_responder * 1) + hazard_penalty
                return score

            # Sort neighbors based on the score (lowest score is best)
            neighbors = sorted(neighbors, key=calculate_score)

            # Choose the best neighbor
            best_neighbor = neighbors[0] if neighbors else None

            if best_neighbor:
                print(f"{self.agent.agent_name} selected {best_neighbor.name} based on updated scoring system.")
            else:
                print(f"{self.agent.agent_name} could not find a valid neighbor.")

            return best_neighbor
            
            '''

        def get_next_room_towards_exit(self, target_room): #Standard Algorithm
            neighbors = self.agent.location.get_neighbors()
            # Filter out rooms to avoid (due to fire or earthquake)
            neighbors = [room for room in neighbors if room.name not in self.agent.avoid_rooms]
            if not neighbors:
                update=f"No available rooms to move towards! {self.agent.agent_name} is stuck."
                self.agent.environment.add_update(update)
                print(update)
                return None
            # Sort neighbors by distance to the target room and pick the closest
            neighbors = sorted(neighbors, key=lambda room: room.distance_to(target_room))
            return neighbors[0] if neighbors else None

        async def navigate_to_exit(self):
            exit_a = self.agent.environment.assembly_points[0]
            exit_b = self.agent.environment.assembly_points[1]

            # Choose the nearest exit based on a distance calculation
            exit_a_dist = self.agent.location.distance_to(exit_a)
            exit_b_dist = self.agent.location.distance_to(exit_b)
            nearest_exit = exit_a if exit_a_dist <= exit_b_dist else exit_b

            print(f"{self.agent.agent_name} is navigating from {self.agent.location.name} to nearest exit at {nearest_exit.name}")

            # Check if the current location and exit are on the same floor
            if self.agent.location.floor != nearest_exit.floor:
                elevator = self.agent.environment.get_floor(self.agent.location.floor).elevator
                if self.agent.mobility == "disabled":
                    destination = elevator
                    method = "elevator"
                else:
                    staircase = self.agent.environment.get_floor(self.agent.location.floor).staircase
                    dist_elev = self.agent.location.distance_to(elevator)
                    dist_stairs = self.agent.location.distance_to(staircase)
                    if dist_elev <= dist_stairs:
                        destination = elevator
                        method = "elevator"
                    else:
                        destination = staircase
                        method = "staircase"

                update=f"{self.agent.agent_name} is moving to {destination.name} to change floors using the {method}."
                self.agent.environment.add_update(update)
                print(update)
                # Navigate to the elevator or staircase first
                while self.agent.location != destination:
                    next_room = self.get_next_room_towards_exit(destination)
                    await asyncio.sleep(self.agent.pace)
                    print(f"{self.agent.agent_name} moved from {self.agent.location.name} to {next_room.name}")
                    self.agent.location = next_room
                # After reaching elevator or staircase, move to the target floor
                dest_room = self.agent.environment.get_room(nearest_exit.floor - 1, destination.coordinates[1],
                                                      self.agent.location.coordinates[2])
                self.agent.location = dest_room
                await self.elevator_request()
                await asyncio.sleep(4)
                update=f"{self.agent.agent_name} is now on floor {self.agent.location.floor} after using the {method}. Continuing to the exit."
                self.agent.environment.add_update(update)
                print(update)
            while self.agent.location != nearest_exit:
                next_room = self.get_next_room_towards_exit(nearest_exit)
                await asyncio.sleep(self.agent.pace)
                # Move to the next room and update location
                print(f"{self.agent.agent_name} moved from {self.agent.location.name} to {next_room.name}")
                self.agent.location = next_room
            if self.agent.location == nearest_exit:
                update=f"{self.agent.agent_name} has arrived at the exit at {nearest_exit.name}!"
                self.agent.environment.add_update(update)
                print(update)
                self.agent.location="Evacuated"
                self.agent.finish_time=time.time()
                self.agent.is_evacuated=True

        async def redirect_route_to_exit(self):
            await self.navigate_to_exit()
           
        def get_is_evacuated(self):
            return self.agent.is_evacuated

'''
_____________________________________________________________________________________________________________________

'''

class EmergencyResponderAgent(spade.agent.Agent):
    def __init__(self, jid, password, responder_name, environment, job):
        super().__init__(jid, password)
        self.responder_name=responder_name
        self.environment = environment
        self.location=environment.get_random_room()
        self.job = job

    async def setup(self):
        print(f"Emergency Responder Agent {self.responder_name} is ready.")
        self.add_behaviour(self.EmergencyBehaviour())

    class EmergencyBehaviour(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=0.1)
            # Check for fire in rooms
            if msg:
                if msg.body.startswith("Fire") and self.agent.job == "firefighter":
                    room = msg.body.split()[-1]  # Extract room name to avoid
                    room = self.agent.environment.get_room(int(room[0])-1,int(room[1]),int(room[2]))
                    room.begin=time.time()
                    await self.agent.navigate_to_room(room)
                    update=f"{self.agent.responder_name} has arrived at {room.name}. Fire extinguished."
                    self.agent.environment.add_update(update)
                    print(update)
                    self.agent.environment.responses+=1
                    self.agent.environment.num_fires[0]+=1
                    room.is_on_fire = False
                    room.end=time.time()
                    self.agent.environment.times.append(room.end-room.begin) 
                    room.noted_fire = False

                elif msg.body.startswith("Earthquake") and self.agent.job=="Rescue Worker":
                    room = msg.body.split()[-1]  # Extract room name to avoid
                    room = self.agent.environment.get_room(int(room[0])-1,int(room[1]),int(room[2]))
                    room.begin=time.time()
                    await self.agent.navigate_to_room(room)
                    update=f"{self.agent.responder_name} has arrived at {room.name}. Wreckage removed."
                    self.agent.environment.add_update(update)
                    print(update)
                    self.agent.environment.responses+=1
                    self.agent.environment.num_earthquakes[0]+=1
                    room.end=time.time()
                    self.agent.environment.times.append(room.end-room.begin) 
                    room.is_damaged = False
                    room.noted_earthquake = False
                    
                elif msg.body.startswith("Attack") and self.agent.job=="Security Officer":
                    room = msg.body.split()[-1]  # Extract room name to avoid
                    room = self.agent.environment.get_room(int(room[0])-1,int(room[1]),int(room[2]))
                    room.begin=time.time()
                    await self.agent.navigate_to_room(room)
                    update=f"{self.agent.responder_name} has arrived at {room.name}. Attack controlled."
                    self.agent.environment.add_update(update)
                    print(update)
                    self.agent.environment.num_attacks[0]+=1
                    self.agent.environment.responses+=1
                    room.end=time.time()
                    self.agent.environment.times.append(room.end-room.begin) 
                    room.is_taken = False
                    room.noted_attack = False

                elif msg.body.startswith("Paramedics") and self.agent.job=="Paramedic":
                    room = msg.body.split()[-1]  # Extract room name to avoid
                    room = self.agent.environment.get_room(int(room[0])-1,int(room[1]),int(room[2]))
                    room.begin=time.time()
                    await self.agent.navigate_to_room(room)
                    room.end=time.time()
                    self.agent.environment.times.append(room.end-room.begin) 
                    update=f"{self.agent.responder_name} has arrived at {room.name}. Providing medical help!"
                    self.agent.environment.add_update(update)
                    print(update)
                    self.agent.environment.responses+=1
                    await asyncio.sleep(2)
                    update=f"{self.agent.responder_name} is leaving! Every occupant is now ok!"
                    self.agent.environment.add_update(update)
                    print(update)
            

    def get_next_room_towards_destination(self, target_room):

        neighbors = self.location.get_neighbors()
        # Filter out rooms to avoid (due to fire or earthquake)
        neighbors = [room for room in neighbors]
        if not neighbors:
            print(f"No available rooms to move towards! {self.responder_name} is stuck.")
            return None
        # Sort neighbors by distance to the target room and pick the closest
        neighbors = sorted(neighbors, key=lambda room: room.distance_to(target_room))
        return neighbors[0] if neighbors else None

    async def navigate_to_room(self, room):

        # Check if the current location and exit are on the same floor
        if self.location.floor != room.floor:
            elevator = self.environment.get_floor(self.location.floor).elevator
            staircase = self.environment.get_floor(self.location.floor).staircase
            dist_elev = self.location.distance_to(elevator)
            dist_stairs = self.location.distance_to(staircase)
            if dist_elev <= dist_stairs:
                destination = elevator
                method = "elevator"
            else:
                destination = staircase
                method = "staircase"
            update=f"{self.responder_name} is moving to {destination.name} to change floors using the {method}."
            self.environment.add_update(update)
            print(update)
            # Navigate to the elevator or staircase first
            while self.location != destination:
                next_room = self.get_next_room_towards_destination(destination)
                await asyncio.sleep(1.5)
                print(f"{self.responder_name} moved from {self.location.name} to {next_room.name}")
                self.location = next_room
            # After reaching elevator or staircase, move to the target floor
            dest_room = self.environment.get_room(room.floor - 1, destination.coordinates[1],
                                                  self.location.coordinates[2])
            self.location = dest_room
            await asyncio.sleep(4)
            update=f"{self.responder_name} is now on floor {self.location.floor} after using the {method}."
            self.environment.add_update(update)
            print(update)
        while self.location != room:
            next_room = self.get_next_room_towards_destination(room)
            await asyncio.sleep(1.5)
            # Move to the next room and update location
            print(f"{self.responder_name} moved from {self.location.name} to {next_room.name}")
            self.location = next_room
        if self.location == room:
            return
            
'''
_________________________________________________________________________________________________________________
'''

class BuildingManagementAgent(spade.agent.Agent):
    def __init__(self, jid, password, environment, management_name):
        super().__init__(jid, password)
        self.environment = environment  # Reference to building environment with exits, elevators, rooms, etc.
        self.alarm_triggered = False
        self.elevator_locked = False  # Elevator is locked by default during emergencies
        self.room_status = {}
        self.management_name=management_name
        self.evac_msg=False  # Track each room's status (e.g., fire, damage, occupancy)

    async def setup(self):
        print(f"Building Management Agent {str(self.management_name)} is ready.")
        self.add_behaviour(self.SendEvacuationInstructionsBehaviour())
        self.add_behaviour(self.ManageBuildingBehaviour())
        self.add_behaviour(self.ElevatorRequestHandler())
        
    class SendEvacuationInstructionsBehaviour(OneShotBehaviour):
        async def run(self):
            occupants = self.agent.environment.agents.keys()
            tasks = []
            for i in occupants:
                # Send an evacuation message to each OccupantAgent
                msg = Message(to=str(i))  # Replace with real occupant agent JIDs
                msg.body = "EVACUATE"  # The action or instruction for the occupant agent
                tasks.append(self.send(msg))
                print(f"Sent evacuation message to {msg.to}")
            await asyncio.gather(*tasks)

    class ElevatorRequestHandler(CyclicBehaviour):
        async def run(self):
            msg = await self.receive(timeout=0.5)           
            if msg and msg.body.startswith("Send Elevator"):
                await self.unlock_elevator_for_disabled()
                confirmation_msg = Message(to=str(msg.sender))
                confirmation_msg.body = "ELEVATOR ACCESS GRANTED"
                await self.send(confirmation_msg)
                update=f"Elevator access granted."
                self.agent.environment.add_update(update)
                print(update)
                await asyncio.sleep(1)
                await self.lock_elevator()
        async def lock_elevator(self):
            self.elevator_locked = True
            print("Elevator locked for general use due to hazard, but it can be unlocked for disabled occupants if needed.")

        async def unlock_elevator_for_disabled(self):
            self.elevator_locked = False

    class ManageBuildingBehaviour(CyclicBehaviour):
        async def run(self):
            # Monitor the environment for any fire or earthquake events
            await asyncio.sleep(0.05)  # Check every 0.5 seconds (can be adjusted)
            # Check for fire in rooms
            for floor in self.agent.environment.floors:
                for row in floor.rooms:
                    for room in row:
                        if room.is_on_fire and room.noted_fire==False:
                            for someone in self.agent.environment.agents.values():
                                if someone.location==room:
                                    await self.send_paramedics(room, "Fire")
                            self.agent.environment.num_fires[1]+=1
                            update=f"{self.agent.management_name} detected fire in {room.name}!"
                            self.agent.environment.add_update(update)
                            print(update)
                            room.noted_fire=True
                            # Send evacuation instruction to avoid fire
                            await self.send_emergency_instruction(room, "Fire")
                            await self.send_evacuate_instruction(room,"Fire")
                        if room.is_damaged and room.noted_earthquake==False:
                            for someone in self.agent.environment.agents.values():
                                if someone.location==room:
                                    await self.send_paramedics(room, "Earthquake")
                            if room.light==False:
                                update=f"{self.agent.management_name} detected lights off due to Earthquake"
                                self.agent.environment.add_update(update)
                                print(update)
                                await asyncio.sleep(1)
                                room.light=True
                                update=f"Lights turned on"
                                self.agent.environment.add_update(update)
                                print(update)
                            self.agent.environment.num_earthquakes[1]+=1
                            room.noted_earthquake=True
                            if room in self.agent.environment.assembly_points:
                                self.agent.environment.assembly_points.remove(room)
                                update=f"Assembly Point {room.name} blocked due to earthquake damage"
                                self.agent.environment.add_update(update)
                                print(update)
                                await self.send_assembly_point_blocked(room)
                            else:
                                update=f"{self.agent.management_name} detected earthquake damage in {room.name}!"
                                self.agent.environment.add_update(update)
                                print(update)
                                # Send evacuation instruction to avoid damaged rooms
                                await self.send_evacuate_instruction(room,"Earthquake")
                                await self.send_emergency_instruction(room, "Earthquake")
                        if room.is_taken and room.noted_attack==False:
                            for someone in self.agent.environment.agents.values():
                                if someone.location==room:
                                    await self.send_paramedics(room, "Attack")
                            update=f"{self.agent.management_name} detected attack in {room.name}!"
                            self.agent.environment.add_update(update)
                            print(update)
                            self.agent.environment.num_attacks[1]+=1
                            room.noted_attack=True
                            await self.send_emergency_instruction(room, "Attack")
                            await self.send_evacuate_instruction(room,"Attack")
                                                            

        async def send_evacuate_instruction(self, room, why):
            # Send evacuation instruction to all occupants to avoid this room
            update=f"Agents will avoid {room.name} due to {why}"
            self.agent.environment.add_update(update)
            print(update)
            occupants = self.agent.environment.agents.keys()
            for occupant in occupants:
                msg = Message(to=str(occupant))
                msg.body = f"Due to {why}, avoid room {room.name}"
                await self.send(msg)
                
        async def send_paramedics(self, room, why):
            agents = self.agent.environment.emergency_agents.keys()
            for agent in agents:
                msg = Message(to=str(agent))
                msg.body = f"Paramedics to {room.name}!"
                await self.send(msg)
                
        async def send_emergency_instruction(self, room, why):
            agents = self.agent.environment.emergency_agents.keys()
            for agent in agents:
                msg = Message(to=str(agent))
                msg.body = f"{why} in {room.name}"
                await self.send(msg)

        async def send_assembly_point_blocked(self, room):
            occupants = self.agent.environment.agents.keys()
            for occupant in occupants:
                msg = Message(to=str(occupant))
                msg.body = f"Assembly room {room.name} blocked due to earthquake damage."
                await self.send(msg)
