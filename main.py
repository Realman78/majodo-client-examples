import tkinter as tk
import requests
import socket
import json
import threading

token = ""
colors = ['red', 'blue', 'green']
screen = "main"
scheduled_task_id = None


def notify_server_of_position():
    coords = canvas.coords(rect)
    serialized_data = json.dumps(coords)
    s.sendto(serialized_data.encode(), ("127.0.0.1", 1934))


def move_left(event):
    canvas.move(rect, -10, 0)
    notify_server_of_position()


def move_right(event):
    canvas.move(rect, 10, 0)
    notify_server_of_position()


def move_up(event):
    canvas.move(rect, 0, -10)
    notify_server_of_position()


def move_down(event):
    canvas.move(rect, 0, 10)
    notify_server_of_position()


roomPlayers = {}


def listen_for_messages(s):
    s.settimeout(60)
    while True:
        try:
            data, addr = s.recvfrom(1024)
            [message, type] = decode_data(data)
            address, coordinates_str = message.split(";#")

            # Extract the first coordinate from the coordinates string
            coords = coordinates_str.strip("[]").split(",")
            x, y = int(float(coords[0])), int(float(coords[1]))

            if address in roomPlayers:
                rect_id = roomPlayers[address]
                canvas.coords(rect_id, x, y, x + 50, y + 50)
            else:
                # Otherwise, create a new rectangle and store its ID in the dictionary
                rect_id = canvas.create_rectangle(x, y, x + 50, y + 50,
                                                  fill=colors[len(roomPlayers) + 1])  # Adjust color as needed
                roomPlayers[address] = rect_id

        except socket.timeout:
            # TODO implement fetching positions from server
            print("Receiving data timed out. Retrying...")


def udp_echo_server(ip, port):
    # Create a UDP socket
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.bind((ip, port))
        print(f"Server started on {ip}:{port}")

        while True:
            data, addr = s.recvfrom(1024)
            [content, type] = decode_data(data)

            # Respond back to the client
            response_message = f"Echoing: {data.decode()}"
            s.sendto(response_message.encode(), addr)


def decode_data(data):
    decoded_str = data.decode('utf-8')

    parsed_obj = json.loads(decoded_str)

    content = parsed_obj.get("content", None)
    message_type = parsed_obj.get("type", None)

    return [content, message_type]


def decode_join_data(data):
    decoded_str = data.decode('utf-8')

    parsed_obj = json.loads(decoded_str)

    message_type = parsed_obj.get("type", None)
    uid = parsed_obj.get("uid", None)
    room_id = parsed_obj.get("roomId", None)

    return [message_type, uid, room_id]


def on_create_button_click():
    # This function will be called when the button is clicked
    global s
    # FIRST: SEND A REQUEST TO INITALIZE ROOM CREATION

    connect_init_query = requests.post("http://127.0.0.1:3000/api/rooms/create")
    response = connect_init_query.json()
    token = response["data"]["token"]

    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Set the socket timeout so it doesn't block indefinitely
    s.settimeout(5)

    # RESPONSE RETURNS TOKEN WHICH YOU ARE SENDING USING UDP BELOW (THIRD ARROW ON DIAGRAM)

    s.sendto(token.encode(), ("127.0.0.1", 1934))

    try:
        data, addr = s.recvfrom(1024)
        [type, uid, room_id] = decode_join_data(data)
        if type == 3:
            # IF THIS SUCCEEDS, YOU ARE IN A ROOM NOW! 
            root.destroy()
            # START LISTENING FOR UDP MESSAGES ON ANOTHER THREAD
            threading.Thread(target=listen_for_messages, args=(s,)).start()
            open_new_screen(player_color=colors[0])


    except socket.timeout:
        print("No response received.")
        return None


def open_new_screen(player_color):
    global canvas, rect
    global screen
    global scheduled_task_id

    # Cancel the scheduled task before destroying root
    if scheduled_task_id:
        root.after_cancel(scheduled_task_id)
    new_root = tk.Tk()
    new_root.title("Game")

    # new_root.attributes("-fullscreen", True)

    canvas = tk.Canvas(new_root, width=500, height=500, bg='white')
    canvas.pack(fill=tk.BOTH, expand=True)

    # Draw a rectangle in the middle
    rect = canvas.create_rectangle(150, 140, 200, 190, fill=player_color)

    new_root.bind("a", move_left)
    new_root.bind("d", move_right)
    new_root.bind("w", move_up)
    new_root.bind("s", move_down)

    screen = "game"
    notify_server_of_position()
    new_root.mainloop()



def fetch_and_create_buttons():
    global scheduled_task_id

    for widget in button_frame.winfo_children():
        widget.destroy()

    # Mock API call. Replace with your actual API request logic.
    response = requests.get('http://127.0.0.1:3000/api/rooms')

    # Assuming the API returns a JSON object with a list of items.
    items = response.json()

    for item in items["data"]:
        button = tk.Button(button_frame, text=item, command=lambda i=item: on_button_click(i))
        button.pack(pady=5)

    # Schedule this function to run again after 10 seconds and store its ID.
    scheduled_task_id = root.after(10000, lambda: fetch_and_create_buttons())


def on_button_click(item):
    global s
    body = {"roomName": item}
    connect_init_query = requests.post("http://127.0.0.1:3000/api/rooms/join", data=body)
    response = connect_init_query.json()
    token = response["data"]["token"]
    print(token)
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    # Set the socket timeout so it doesn't block indefinitely
    s.settimeout(5)

    # Send data
    s.sendto(token.encode(), ("127.0.0.1", 1934))
    # Wait for a response on the same port
    try:
        data, addr = s.recvfrom(1024)
        [type, uid, room_id] = decode_join_data(data)
        if type == 3:
            root.destroy()
            threading.Thread(target=listen_for_messages, args=(s,)).start()
            open_new_screen(player_color=colors[len(roomPlayers)])

            # Respond back to the client
            # response_message = f"Echoing: {data.decode()}"
            # s.sendto(response_message.encode(), addr)
    except socket.timeout:
        print("No response received.")
        return None


# Create the main window
root = tk.Tk()
root.title("Connect Button")
root.geometry("400x300")

# Create a button and add it to the window
create_button = tk.Button(root, text="Create", command=on_create_button_click)
create_button.pack(pady=20)  # Add some padding around the button

input_prompt = tk.Entry(root, text="Room name")
input_prompt.pack(pady=20)

button_frame = tk.Frame(root)
button_frame.pack(pady=20)
fetch_and_create_buttons()
# Start the main loop to show the window
root.mainloop()
