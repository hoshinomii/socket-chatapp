import socket
import select
import sys
import os
import time
import threading

# Parse command line arguments for debug mode
DEBUG = False
args = sys.argv[:]
if "--debug" in args:
    DEBUG = True
    args.remove("--debug")
    print("Debug mode enabled")

def debug_print(message):
    if DEBUG:
        timestamp = time.strftime("%H:%M:%S", time.localtime())
        print(f"[DEBUG {timestamp}] {message}", file=sys.stderr, flush=True)

# Helper function to check if msvcrt is available
def msvcrt_available():
    try:
        import msvcrt
        return True
    except ImportError:
        return False

if len(args) != 3:
    print("Usage: script IP_address port [--debug]")
    sys.exit()
IP_address = str(args[1])
Port = int(args[2])

server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
try:
    server.connect((IP_address, Port))
except ConnectionRefusedError:
    print(f"Unable to connect to server at {IP_address}:{Port}")
    sys.exit()
except Exception as e:
    print(f"Connection error: {e}")
    sys.exit()

# --- Authentication Sequence ---
try:
    sys.stdout.write(server.recv(2048).decode())
    sys.stdout.flush()
    username = input()
    server.send(username.encode())

    sys.stdout.write(server.recv(2048).decode())
    sys.stdout.flush()
    password = input()
    server.send(password.encode())

    response = server.recv(2048).decode()
    if response.startswith("ERROR"):
        print(response)
        server.close()
        sys.exit()
    else:
        print(response)
except Exception as e:
    print(f"Error during authentication: {e}")
    server.close()
    sys.exit()

# Flag to indicate if the client is running
running = True
prompt = f"[{username}] "

# Function to display the prompt
def show_prompt():
    sys.stdout.write(prompt)
    sys.stdout.flush()

# Thread function for receiving messages from server
def receive_messages():
    global running
    debug_print("Receive thread started")
    while running:
        try:
            debug_print("Waiting for server messages...")
            message = server.recv(2048).decode()
            if not message:
                debug_print("Empty message received, server disconnected")
                print("\nConnection closed by server")
                running = False
                break
            
            # Print the received message with a newline before it to separate from prompt
            debug_print(f"Received: {message.strip()}")
            sys.stdout.write("\r" + " " * len(prompt) + "\r")  # Clear prompt
            print(message, end='')
            sys.stdout.flush()
            show_prompt()  # Re-show the prompt
        except Exception as e:
            debug_print(f"Error in receive thread: {e}")
            print(f"\nError receiving: {e}")
            running = False
            break
    debug_print("Receive thread ended")

# Thread function for sending messages to server
def send_messages():
    global running
    debug_print("Send thread started (main thread)")
    show_prompt()  # Show initial prompt
    
    while running:
        try:
            # Read input from user
            debug_print("Waiting for user input...")
            user_input = input()
            
            if not running:
                debug_print("Client no longer running, exiting send loop")
                break
                
            if user_input:
                debug_print(f"Sending: {user_input}")
                try:
                    server.send(user_input.encode())
                    debug_print("Message sent successfully")
                except Exception as e:
                    debug_print(f"Send error: {e}")
                    print(f"\nError sending: {e}")
                    running = False
                    break
            
            # Show the prompt again after sending
            show_prompt()
        except (KeyboardInterrupt, EOFError):
            debug_print("KeyboardInterrupt/EOFError detected")
            running = False
            break
        except Exception as e:
            debug_print(f"Input exception: {e}")
            print(f"\nInput error: {e}")
            time.sleep(0.1)  # Small delay to prevent CPU hogging
    debug_print("Send thread ended")

# Start the receive thread
debug_print("Starting receive thread")
receive_thread = threading.Thread(target=receive_messages)
receive_thread.daemon = True
receive_thread.start()

# --- Main Loop ---
try:
    debug_print("Entering main send loop")
    send_messages()  # This will run in the main thread
except KeyboardInterrupt:
    debug_print("KeyboardInterrupt in main thread")
    print("\nDisconnecting...")
except Exception as e:
    debug_print(f"Exception in main thread: {e}")
    print(f"Error: {e}")
finally:
    debug_print("Cleaning up client resources")
    running = False
    try:
        server.close()
        debug_print("Server socket closed")
    except:
        debug_print("Error closing server socket")
    # Give the threads a moment to clean up
    time.sleep(0.5)
    debug_print("Client shutdown complete")

