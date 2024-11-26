import spade
import random
import asyncio
from environment import Building
from agents import OccupantAgent, EmergencyResponderAgent, BuildingManagementAgent
import dash
from dash import dcc, html
from threading import Thread
from dash.dependencies import Input, Output
import plotly.graph_objs as go
import csv

# Initialize Dash app
app = dash.Dash(__name__)

# Initialize global variables
performance_metrics = [0] * 6
agent_locations = ""
measures = [None, None, None]
active_situations = ""  # To store active situations of rooms
recent_updates=""
final_metrics=""

# Define the Dash layout
app.layout = html.Div(
    children=[
        html.Div(
            children=[
                html.H1("Building Evacuation Simulation", style={"text-align": "center", "color": "#2E86C1"}),
            ],
            style={
                "backgroundColor": "#D5DBDB", 
                "padding": "30px", 
                "borderRadius": "10px",
                "boxShadow": "0 4px 8px rgba(0, 0, 0, 0.2)",
                "marginBottom": "30px"
            },
        ),

        # Main container for left and right side sections
        html.Div(
            children=[
                # Left container for Building Structure, Performance Metrics, and Agent Locations
                html.Div(
                    children=[
                        # Building Structure Section
                        html.Div(
                            children=[
                                html.H3("Building Structure", style={"color": "#2874A6", "font-size": "24px"}),
                                html.Div(
                                    children=[
                                        html.P(id="measures", style={"font-size": "18px", "color": "#1F618D"}),
                                    ],
                                    style={"padding": "20px", "borderRadius": "10px", "backgroundColor": "#E8F8F5", "boxShadow": "0 4px 8px rgba(0, 0, 0, 0.1)"},
                                ),
                            ],
                            style={"marginBottom": "30px", "padding": "20px", "borderRadius": "15px", "backgroundColor": "#D5DBDB"},
                        ),

                        # Performance Metrics Section
                        html.Div(
                            children=[
                                html.H3("Performance Metrics", style={"color": "#2874A6", "font-size": "24px"}),
                                html.Div(
                                    children=[
                                        html.P(id="fires-metrics", style={"font-size": "18px", "color": "#1F618D"}),
                                        html.P(id="earthquake-metrics", style={"font-size": "18px", "color": "#1F618D"}),
                                        html.P(id="attack-metrics", style={"font-size": "18px", "color": "#1F618D"}),
                                    ],
                                    style={"padding": "20px", "borderRadius": "10px", "backgroundColor": "#E8F8F5", "boxShadow": "0 4px 8px rgba(0, 0, 0, 0.1)"},
                                ),
                            ],
                            style={"marginBottom": "30px", "padding": "20px", "borderRadius": "15px", "backgroundColor": "#D5DBDB"},
                        ),

                        # Agent Locations Section
                        html.Div(
                            children=[
                                html.H3("Agent Locations", style={"color": "#2874A6", "font-size": "24px"}),
                                html.Div(
                                    children=[
                                        html.Pre(id="agentlocations", style={"font-size": "18px", "color": "#1F618D"}),
                                    ],
                                    style={"padding": "20px", "borderRadius": "10px", "backgroundColor": "#E8F8F5", "boxShadow": "0 4px 8px rgba(0, 0, 0, 0.1)"},
                                ),
                            ],
                            style={"marginBottom": "30px", "padding": "20px", "borderRadius": "15px", "backgroundColor": "#D5DBDB"},
                        ),
                    ],
                    style={"flex": "1", "display": "flex", "flexDirection": "column"},  # Flex container for the left side
                ),

                # Right container for Active Situations and Recent Updates (aligned with agent locations)
                html.Div(
                    children=[
                        html.H3("Active Situations in Rooms", style={"color": "#2874A6", "font-size": "24px"}),
                        html.Div(
                            children=[
                                html.Pre(id="activesituations", style={"font-size": "18px", "color": "#1F618D"}),
                            ],
                            style={"padding": "20px", "borderRadius": "10px", "backgroundColor": "#E8F8F5", "boxShadow": "0 4px 8px rgba(0, 0, 0, 0.1)"},
                        ),
                        html.H3("Recent Updates", style={"color": "#2874A6", "font-size": "24px"}),
                        html.Div(
                            children=[
                                html.Pre(id="recentupdates", style={"font-size": "20px", "color": "#1F618D"}),
                            ],
                            style={"padding": "20px", "borderRadius": "10px", "backgroundColor": "#E8F8F5", "boxShadow": "0 4px 8px rgba(0, 0, 0, 0.1)"},
                        ),
                        html.H3("Final Simulation Metrics", style={"color": "#2874A6", "font-size": "24px"}),
                        html.Div(
                            children=[
                                html.Pre(id="finalmetrics", style={"font-size": "20px", "color": "#1F618D"}),
                            ],
                            style={"padding": "20px", "borderRadius": "10px", "backgroundColor": "#E8F8F5", "boxShadow": "0 4px 8px rgba(0, 0, 0, 0.1)"},
                        ),
                    ],
                    style={
                        "flex": "1", 
                        "height": "100%", 
                        "overflow": "auto", 
                        "padding": "20px", 
                        "borderRadius": "15px", 
                        "backgroundColor": "#D5DBDB",
                        "display": "flex", 
                        "flexDirection": "column",
                    },  # Ensure both Active Situations and Recent Updates are stacked vertically
                ),
            ],
            style={"display": "flex", "gap": "20px", "height": "100vh"},  # Flex container to align left and right side sections
        ),

        # Interval Component to Update Every 0.5s
        dcc.Interval(
            id="interval-component",
            interval=500,  # Update every 0.5 seconds
            n_intervals=0
        )
    ],
    style={"fontFamily": "Arial, sans-serif", "backgroundColor": "#F4F6F6", "padding": "20px"}
)

# Update performance metrics and active room situations every interval (i.e., 0.5 seconds)
@app.callback(
    [
        Output("fires-metrics", "children"),
        Output("earthquake-metrics", "children"),
        Output("attack-metrics", "children"),
        Output("agentlocations", "children"),
        Output("measures", "children"),
        Output("activesituations", "children"),  # Add active situations output
        Output("recentupdates", "children"),
        Output("finalmetrics", "children"),
    ],
    [Input("interval-component", "n_intervals")]
)
def update_metrics(n):
    # Access global performance metrics
    fires_extinguished = performance_metrics[0]
    total_fires = performance_metrics[1]
    earthquakes = performance_metrics[2]
    total_earthquakes = performance_metrics[3]
    attacks_controlled = performance_metrics[4]
    total_attacks = performance_metrics[5]
    agentlocations=agent_locations
    activesituations = active_situations
    recentupdates = recent_updates
    finalmetrics=final_metrics

    # Return the active situations that were set in the main function
    return (
        f"Fires Extinguished / Total Fires: {fires_extinguished}/{total_fires} ({fires_extinguished/total_fires*100 if total_fires != 0 else 0:.1f}%)",
        f"Earthquakes Cleaned / Total Earthquakes: {earthquakes}/{total_earthquakes} ({earthquakes/total_earthquakes*100 if total_earthquakes!=0 else 0:.1f}%)",
        f"Attacks Controlled / Total Attacks: {attacks_controlled}/{total_attacks} ({attacks_controlled/total_attacks*100 if total_attacks!=0 else 0:.1f}%)",
        agentlocations,
        f"This building has {measures[0]} floors and {measures[1]}x{measures[2]} structure!",
        activesituations,  # Show the active situations for rooms
        recentupdates,
        finalmetrics,
    )


def run_dash(app):
    app.run_server(debug=True, use_reloader=False)

async def main():
    dash_thread = Thread(target=run_dash, args=(app,))
    dash_thread.start()
    building = Building()
    global measures
    measures = [building.num_floors, building.rows, building.cols]
    building.connect_elevators()
    building.connect_staircases()
    num_agents=random.randint(4,8)
    agents_dict = {}
    for i in range(num_agents):
        agent_name = f"occupant_agent_{i+1}"
        jid = f"occupant{i+1}@localhost"
        password = "password"
        name = f"Agent {i+1}"
        status = "able-bodied" if i % 2 == 0 else "disabled"
        agents_dict[agent_name] = OccupantAgent(jid, password, name, building, status)
    emergency_responder_agent_1 = EmergencyResponderAgent("responder1@localhost", "password", "Fire-fighter", building, "firefighter")
    emergency_responder_agent_2 = EmergencyResponderAgent("responder2@localhost", "password", "Rescue Worker", building, "Rescue Worker")
    emergency_responder_agent_3 = EmergencyResponderAgent("responder3@localhost", "password", "Paramedic", building, "Paramedic")
    emergency_responder_agent_4 = EmergencyResponderAgent("responder4@localhost", "password", "Security Officer", building, "Security Officer")
    building_management_agent = BuildingManagementAgent("management@localhost", "password", building, "Building Management")
    for agent in agents_dict.values():
    	building.add_agent(agent)
    building.add_emergency_agent(emergency_responder_agent_1)
    building.add_emergency_agent(emergency_responder_agent_2)
    building.add_emergency_agent(emergency_responder_agent_3)
    building.add_emergency_agent(emergency_responder_agent_4)
    building.add_management_agent(building_management_agent)
    
    for agent in agents_dict.values():
    	await agent.start(auto_register=True)
    await emergency_responder_agent_1.start(auto_register=True)
    await emergency_responder_agent_2.start(auto_register=True)
    await emergency_responder_agent_3.start(auto_register=True)
    await emergency_responder_agent_4.start(auto_register=True)
    await building_management_agent.start(auto_register=True)
    
    # Start simulation
    while not building.is_building_evacuated():
        building.simulate_step()
        await asyncio.sleep(1)

        # Update global performance metrics
        global performance_metrics
        performance_metrics = [building.num_fires[0], building.num_fires[1], building.num_earthquakes[0], building.num_earthquakes[1], building.num_attacks[0], building.num_attacks[1]]

        # Update agent locations dynamically
        global agent_locations
        agent_locations=""
        for i in building.agents.values():
            agent_locations+=f"{i.agent_name} Location: {i.location.name if hasattr(i.location, 'name') else i.location}\n"
        
        # Update active situations
        global active_situations
        active_situations = ""
        for floor in building.floors:
            for i in range(floor.num_cols):
                for j in range(floor.num_rows):
                    room=floor.get_room(j,i)
                    if room.is_on_fire:
                        active_situations += f"Fire in {room.name}.\n"
                    if room.is_damaged:
                        active_situations += f"Earthquake damage in {room.name}.\n"
                    if room.is_taken:
                        active_situations += f"Attack in {room.name}.\n"
                        
        global recent_updates
        recent_updates=building.updates
        
        global final_metrics
        final_metrics=""
        time_spent_list=[]
        if building.is_building_evacuated():
            for i in building.agents.values():
                time_spent = i.finish_time - building.begin
                time_spent_list.append(time_spent)
            for i in range (len(time_spent_list)):
                final_metrics+=f"Agent {i+1} took {time_spent_list[i]:.2f} to evacuate!\n"
            total_time = max(time_spent_list)
            final_metrics+=f"Total Evacuation Time: {total_time:.2f}\n"
            final_metrics+=f"Number of problems solved by Emergency Responders: {len(building.times)}\n"
            final_metrics+=f"Average Response Time of Emergency Responders: {sum(building.times)/len(building.times) if len(building.times) != 0 else 0:.2f}\n"
        
    print("Every Occupant evacuated! Success!")
    values = building.performance_metrics()
    
    for agent in agents_dict.values():
    	await agent.stop()
    await emergency_responder_agent_1.stop()
    await emergency_responder_agent_2.stop()
    await emergency_responder_agent_3.stop()
    await emergency_responder_agent_4.stop()
    await building_management_agent.stop()
    return values

async def run_tests():
    values_total = [0] * 11
    n = 50
    results = []  # Store results for each test

    for i in range(n):
        print(f"Running test {i + 1}...")
        values = await main()
        values_total = [x + y for x, y in zip(values_total, values)]
        results.append(values)  # Add individual test results to the list

    # Calculate averages and summaries
    avg_evacuation_time = values_total[9] / n if n > 0 else 0
    avg_response_time = values_total[10] / n if n > 0 else 0
    summary = {
        "Fires Extinguished": f"{values_total[0]}/{values_total[1]}",
        "Earthquakes Resolved": f"{values_total[2]}/{values_total[3]}",
        "Attacks Controlled": f"{values_total[4]}/{values_total[5]}",
        "Agents Evacuated": f"{values_total[6]}/{values_total[7]}",
        "Average Evacuation Time": avg_evacuation_time,
        "Problems Solved by Responders": values_total[8],
        "Average Responder Time": avg_response_time
    }

    # Save results to a CSV file
    with open("original_results.csv", "w", newline="") as file:
        writer = csv.writer(file)
        # Write the header
        writer.writerow([
            "Test", "Fires Extinguished", "Earthquakes Resolved", "Attacks Controlled",
            "Agents Evacuated", "Average Evacuation Time", "Problems Solved",
            "Average Responder Time"
        ])
        # Write individual test results
        for i, result in enumerate(results):
            writer.writerow([i + 1] + result)
        # Write summary row
        writer.writerow([])
        writer.writerow(["Summary"] + list(summary.values()))

    print("Results saved to 'original_results.csv'.")

if __name__ == "__main__":
    asyncio.run(main())

