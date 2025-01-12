import streamlit as st
from pymongo import MongoClient
import bcrypt
import datetime
from bson.objectid import ObjectId

# MongoDB connection setup
client = MongoClient("mongodb://localhost:27017/")  # Local MongoDB connection
db = client["pollconnect"]  # Database name
users = db["users"]  # Collection for users
polls = db["polls"]  # Collection for polls

# Helper functions
def register_user(username, password):
    if users.find_one({"username": username}):
        return "Username already exists!"
    hashed_pw = bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt())
    users.insert_one({"username": username, "password": hashed_pw, "created_at": datetime.datetime.now()})
    return "Registration successful!"

def login_user(username, password):
    user = users.find_one({"username": username})
    if user and bcrypt.checkpw(password.encode("utf-8"), user["password"]):
        return True
    return False

def create_poll(username, question, options):
    poll = {
        "username": username,
        "question": question,
        "options": {option: {"votes": 0, "voters": []} for option in options},
        "comments": [],
        "likes": 0,
        "dislikes": 0,
        "created_at": datetime.datetime.now()
    }
    polls.insert_one(poll)
    return "Poll created successfully!"

def vote_on_poll(poll_id, username, selected_option):
    poll = polls.find_one({"_id": ObjectId(poll_id)})
    
    if not poll:
        return "Poll not found."

    # Check if the user has already voted
    previous_vote = None
    for option, data in poll["options"].items():
        if username in data["voters"]:
            previous_vote = option
            break

    # If the user has voted before, remove their previous vote
    if previous_vote:
        polls.update_one({"_id": ObjectId(poll_id)}, {"$inc": {f"options.{previous_vote}.votes": -1}})
        polls.update_one({"_id": ObjectId(poll_id)}, {"$pull": {f"options.{previous_vote}.voters": username}})

    # Add the new vote
    polls.update_one({"_id": ObjectId(poll_id)}, {"$inc": {f"options.{selected_option}.votes": 1}})
    polls.update_one({"_id": ObjectId(poll_id)}, {"$push": {f"options.{selected_option}.voters": username}})

    return "Vote updated successfully!"

def add_comment(poll_id, comment):
    polls.update_one({"_id": ObjectId(poll_id)}, {"$push": {"comments": comment}})
    return "Comment added!"

def like_poll(poll_id):
    polls.update_one({"_id": ObjectId(poll_id)}, {"$inc": {"likes": 1}})

def dislike_poll(poll_id):
    polls.update_one({"_id": ObjectId(poll_id)}, {"$inc": {"dislikes": 1}})

def delete_poll(poll_id, username):
    poll = polls.find_one({"_id": ObjectId(poll_id)})
    if poll and poll["username"] == username:
        polls.delete_one({"_id": ObjectId(poll_id)})
        return "Poll deleted successfully!"
    else:
        return "You are not authorized to delete this poll."

def update_poll(poll_id, question, options):
    polls.update_one({"_id": ObjectId(poll_id)}, {"$set": {"question": question, "options": {option: {"votes": 0, "voters": []} for option in options}}})
    return "Poll updated successfully!"

def initialize_poll_fields(poll):
    # Ensure all options have 'votes' and 'voters' fields initialized
    for option, data in poll["options"].items():
        if "votes" not in data:
            data["votes"] = 0
        if "voters" not in data:
            data["voters"] = []
    # Ensure likes and dislikes are initialized
    if 'likes' not in poll:
        poll['likes '] = 0
    if 'dislikes' not in poll:
        poll['dislikes'] = 0
    return poll

# Streamlit UI
st.set_page_config(layout="wide")
st.title("PollConnect - A Social Polling Platform")

# Authentication
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.sidebar.header("Login / Register")
    choice = st.sidebar.radio("Choose an option", ["Login", "Register"])

    if choice == "Login":
        username = st.sidebar.text_input("Username")
        password = st.sidebar.text_input("Password", type="password")
        if st.sidebar.button("Login"):
            if login_user(username, password):
                st.session_state.authenticated = True
                st.session_state.username = username
                st.success("Logged in successfully!")
            else:
                st.error("Invalid credentials!")

    elif choice == "Register":
        username = st.sidebar.text_input("Username")
        password = st.sidebar.text_input("Password", type="password")
        if st.sidebar.button("Register"):
            message = register_user(username, password)
            st.sidebar.success(message) if "successful" in message else st.sidebar.error(message)

else:
    # Main application
    st.sidebar.header(f"Welcome, {st.session_state.username}!")
    menu = st.sidebar.radio("Menu", ["Home", "Create Poll", "View Polls", "Logout"])

    if menu == "Home":
        st.write("Welcome to PollConnect! Start creating or participating in polls.")

    elif menu == "Create Poll":
        st.header("Create a New Poll")
        question = st.text_input("Enter your question")
        options = st.text_area("Enter options (one per line)").split("\n")
        if st.button("Create Poll"):
            if question and options:
                message = create_poll(st.session_state.username, question, options)
                st.success(message)
            else:
                st.error("Please provide a question and options.")

    elif menu == "View Polls":
        st.header("Available Polls")
        search_query = st.text_input("Search Polls", "")
        all_polls = list(polls.find())  # Get all polls from the database

        if search_query:
            all_polls = [poll for poll in all_polls if search_query.lower() in poll["question"].lower()]
            if not all_polls:
                st.warning("No such polls found.")
        else:
            st.warning("Please enter a search term.")

        for poll in all_polls:
            poll = initialize_poll_fields(poll)  # Initialize missing fields
            poll_id = str(poll["_id"])  # Convert ObjectId to string for Streamlit compatibility

            # Display poll content with enhanced styling
            st.markdown(
                f"""
                <div style="border: 5px solid #0073e6; border-radius: 15px; padding: 20px; margin-bottom: 30px; background-color: #f9f9f9;">
                    <div style="border-bottom: 2px solid #0073e6; padding-bottom: 10px; margin-bottom: 10px;">
                        <div style="display: flex; align-items: center;">
                            <div style="width: 40px; height: 40px; border-radius: 50%; background-color: #333; color: white; display: flex; justify-content: center; align-items: center; margin-right: 10px;">
                                <span style="font-size: 16px;">{poll['username'][0].upper()}</span>
                            </div>
                            <h4 style="margin: 0; color: #0073e6; font-size: 18px;">{poll['username']}</h4>
                        </div>
                        <h3 style="margin: 10px 0; color: #333; font-size: 20px;">{poll['question']}</h3>
                    </div>
                """, unsafe_allow_html=True)

            # Display poll options
            st.markdown(
                """
                <div style="padding-top: 15px;">
                    <h4 style="margin-bottom: 8px; color: #0073e6; font-size: 16px;">Options:</h4>
                """, unsafe_allow_html=True)

            options = poll["options"]
            total_votes = sum([option["votes"] for option in options.values()])

            for option, data in options.items():
                option_text = f"{option} ({data['votes']} votes)"
                if total_votes > 0:
                    percentage = (data["votes"] / total_votes * 100)
                    option_text += f" - {percentage:.1f}%"

                if st.button(option_text, key=f"vote_{poll_id}_{option}"):
                    try:
                        message = vote_on_poll(poll_id, st.session_state.username, option)
                        st.success(message)
                    except Exception as e:
                        st.error("Error updating vote.")

            # Display comments
            st.markdown("</div>", unsafe_allow_html=True)
            st.markdown("<div style='padding-top: 15px; border-top: 1px solid #ccc; margin-top: 15px;'>", unsafe_allow_html=True)
            st.markdown("<h4 style='margin-bottom: 8px; color: #0073e6; font-size: 16px;'>Comments:</h4>", unsafe_allow_html=True)

            if poll["comments"]:
                for comment in poll["comments"]:
                    st.markdown(f"<p style='margin: 5px 0; padding-left: 10px; font-size: 14px; border-bottom: 1px solid #eee;'>{comment}</p>", unsafe_allow_html=True)
            else:
                st.markdown("<p style='font-size: 14px;'>No comments yet.</p>", unsafe_allow_html=True)

            # Adjusted comment box height
            comment_input = st.text_area(
                "Add your comment here", 
                key=f"comment_{poll_id}", 
                max_chars=100,  # Reduce the maximum number of characters allowed
                height=68  # Set the height to meet the minimum requirement
            )
            if st.button("Submit Comment", key=f"comment_button_{poll_id}") and comment_input:
                add_comment(poll_id, comment_input)
                st.success("Comment added!")

            # Display Like/Dislike buttons
            col1, col2, col3 = st.columns([1, 1, 1])
            with col1:
                if st.button(f"👍 Like ({poll['likes']})", key=f"like_{poll_id}"):
                    like_poll(poll_id)
                    st.success("Poll liked!")
            with col2:
                if st.button(f"👎 Dislike ({poll['dislikes']})", key=f"dislike_{poll_id}"):
                    dislike_poll(poll_id)
                    st.success("Poll disliked!")
            with col3:
                # Share Button
                if st.button("Share", key=f"share_{poll_id}"):
                    st.markdown(
                        f"""
                        <div>
                            <a href="https://twitter.com/intent/tweet?text=Check%20out%20this%20poll!&url=https://yourdomain.com/poll/{poll_id}" target="_blank">
                                Share on Twitter
                            </a><br>
                            <a href="https://api.whatsapp.com/send?text=Check%20out%20this%20poll!%20https://yourdomain.com/poll/{poll_id}" target="_blank">
                                Share on WhatsApp
                            </a><br>
                            <a href="https://www.facebook.com/sharer/sharer.php?u=https://yourdomain.com/poll/{poll_id}" target="_blank">
                                Share on Facebook
                            </a><br>
                            <a href="https://www.instagram.com" target="_blank">
                                Share on Instagram (via link)
                            </a>
                        </div>
                        """, unsafe_allow_html=True)

            # Delete Poll Button (Private)
            if st.session_state.username == poll["username"]:
                if st.button("Delete Poll", key=f"delete_{poll_id}"):
                    message = delete_poll(poll_id, st.session_state.username)
                    st.success(message)

            # Update Poll Button (Universal)
            if st.button("Update Poll", key=f"update_{poll_id}"):
                new_question = st.text_input("New Question", value=poll['question'], key=f"new_question_{poll_id}")
                new_options = st.text_area("New Options (one per line)", value='\n'.join(poll['options'].keys()), key=f"new_options_{poll_id}")
                if st.button("Submit Update", key=f"submit_update_{poll_id}"):
                    message = update_poll(poll_id, new_question, new_options.split("\n"))
                    st.success(message)

    elif menu == "Logout":
        st.session_state.authenticated = False
        st.session_state.username = None
        st.success("Logged out successfully!")