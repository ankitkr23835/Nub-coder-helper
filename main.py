import telethon
import pymongo
import os
import certifi
from telethon import TelegramClient, events, Button
from telethon.errors import UserNotParticipantError, ChatAdminRequiredError
from telethon.tl.functions.messages import ExportChatInviteRequest  # Correct import for invite link
from telethon.tl.types import PeerChannel, ChatAdminRights
from telethon.tl.functions.channels import GetFullChannelRequest
# MongoDB setup
client = pymongo.MongoClient("mongodb+srv://ankitkr23835:air8858@cluster0.cxh2ryf.mongodb.net/?retryWrites=true&w=majority&appName=Cluster0", tlsCAFile=certifi.where())
db = client["telegram_bot"]
collection = db["groups"]
from config import *
# API details
ggg=os.getcwd()
# Create the bot client
bot = TelegramClient(None, api_id, api_hash).start(bot_token=bot_token)

# Check if the bot has necessary permissions in the group and channel
async def check_permissions(event, group_id, new_channel_id):
    # Check if the bot has permission to delete messages in the group
    group_permissions = await bot.get_permissions(group_id, bot._self_id)
    if not group_permissions.delete_messages:
        await event.respond("Bot needs 'Delete Messages' permission in the group to proceed.")
        return False

    # Check if the bot has permission to check channel members and generate invite links
    try:
        channel = await bot.get_entity(new_channel_id)
    except ValueError:
        return await event.respond(
            "Add me to the channel with invite users permission")

    if not channel.admin_rights.invite_users:
        return await event.respond("Bot needs 'Invite Users via Link' permission in the channel to proceed.")
    channel = await bot.get_entity(new_channel_id)
    channel_title= channel.title
    await event.respond(
        f"Channel '{channel_title}' added to the bot. Now every member's messages (excluding admins) "
        f"will be deleted if they are not part of the channel."
    )
    return True

# Command to set the channel ID (/pr <channel_id>)
from telethon.errors import UsernameNotOccupiedError, InviteHashExpiredError, InviteHashInvalidError
import re
async def on_bot_added(event):
    if event.user_added or event.user_joined:
        # Check if the bot was added to the group
        if event.user_id == bot._self_id:
           await start_handler(event)
# Command to show all available commands and their usage
@bot.on(events.NewMessage(pattern='/start', incoming=True))
async def start_handler(event):
    response = (
        "**Bot Commands and Usage**\n\n"
        "1. **/start** - Displays this help message with all commands and their usage.\n\n"
        "2. **/pr <channel_id|@username|invite_link>** - Add a channel to the group where the bot will check if users are part of the channel. Accepts numeric channel IDs, usernames (with @), or invite links.\n"
        "   - Usage: `/pr 123456789` or `/pr @channelusername` or `/pr https://t.me/joinchat/abc123`\n\n"
        "3. **/prs** - List all channels currently set for the group.\n"
        "   - Usage: `/prs`\n\n"
        "4. **/rm <channel_id>** - Remove a specific channel from the group's list.\nCheck /prs for channel id\n"
        "   - Usage: `/rm 123456789`\n\n"
    )

    await event.respond(response)

# Command to set the channel ID (/pr <channel_id or username or private link>)
@bot.on(events.NewMessage(pattern='/pr (.+)', incoming=True, func=lambda e: not e.is_private))
async def set_channel(event):
    sender = await event.get_sender()
    group_id = event.chat_id
    
    # Check if the user is an admin with "Change Group Info" permission or the group owner
    user_permissions = await bot.get_permissions(group_id, sender.id)
    
    if not (user_permissions.is_creator or user_permissions.change_info):
        await event.respond("Only the group owner or an admin with 'Change Group Info' permission can set the channel.")
        return
    
    # Get the channel identifier from the command input
    channel_input = event.pattern_match.group(1).strip()

    try:
        if channel_input.isdigit():
            # If it's a numeric ID, convert to int
            new_channel_id = int(channel_input)
            channel_entity = await bot.get_entity(PeerChannel(new_channel_id))

        elif re.match(r'^@[\w\d_]+$', channel_input):
            # If it's a username starting with @
            channel_entity = await bot.get_entity(channel_input)
            new_channel_id = channel_entity.id

        elif re.match(r'https://t\.me/joinchat/[\w\d_-]+', channel_input):
            # If it's a private channel invite link
            invite_hash = channel_input.split('/')[-1]
            invite = await bot(ImportChatInviteRequest(invite_hash))
            channel_entity = await bot.get_entity(invite.chats[0])
            new_channel_id = channel_entity.id

        else:
            await event.respond("Invalid format. Please provide a valid channel ID, username, or invite link.")
            return

        # Run permission checks
        success = await check_permissions(event, group_id, new_channel_id)

        if success:
            # Store the channel ID for this group in MongoDB
            collection.update_one(
                {"group_id": group_id},
                {"$addToSet": {"channels": new_channel_id}},
                upsert=True
            )
            await event.respond(f"Channel '{channel_entity.title}' added successfully.")

    except (UsernameNotOccupiedError, ValueError):
        await event.respond("Invalid channel username or ID.")
    except (InviteHashExpiredError, InviteHashInvalidError):
        await event.respond("Invalid or expired private invite link.")
    except Exception as e:
        await event.respond(f"An error occurred: {str(e)}")


@bot.on(events.NewMessage(pattern='^/reboot$'))
async def reboot_handler(event):
    user_id = event.sender_id

    # Check if the user is an admin by comparing their user ID with the ones in /home/u219967/W>
    admin_file = f"{ggg}/admin.txt"
    if os.path.exists(admin_file):
        with open(admin_file, "r") as file:
            admin_ids = [int(line.strip()) for line in file.readlines()]
            if user_id in admin_ids:
                await event.respond("Admin command received. Stopping the bot...")
                sys.exit(0)  # Raise a system exit exception to stop the entire code
            else:
                await event.respond("You are not authorized to use this command.")
    else:
        await event.respond("Admin file not found. Please contact the bot admin.")

# Command to list all channels set for the group (/prs)
@bot.on(events.NewMessage(pattern='/prs',incoming=True, func=lambda e: not e.is_private))
async def list_channels(event):
    group_id = event.chat_id
    group = await bot.get_entity(group_id)
    if group.admin_rights is None:
        return await event.respond("Please promote me as admin with atleast message delete permission")
    # Fetch the group's channel data from MongoDB
    group_data = collection.find_one({"group_id": group_id})
    if not group_data or "channels" not in group_data:
        await event.respond("No channels have been added to this group.")
        return

    # List all channel IDs and fetch their details
    channels = group_data["channels"]
    response = "Channels added to this group:\n\n"
    for channel_id in channels:
        try:
            channel_entity = await bot.get_entity(PeerChannel(channel_id))
            channel_info = await bot(GetFullChannelRequest(channel=channel_entity))
            response += f"• Channel Title: {channel_info.full_chat.about} (ID: {channel_id})\n"
        except Exception as e:
            response += f"• Failed to get details for Channel ID: {channel_id} (Error: {str(e)})\n"

    await event.respond(response)

# Command to remove a specific channel (/rm <channel_id>)
@bot.on(events.NewMessage(pattern='/rm (.+)',incoming=True, func=lambda e: not e.is_private))
async def remove_channel(event):
    sender = await event.get_sender()
    group_id = event.chat_id

    # Check if the user is an admin with "Change Group Info" permission or the group owner
    user_permissions = await bot.get_permissions(group_id, sender.id)

    if not (user_permissions.is_creator or user_permissions.change_info):
        await event.respond("Only the group owner or an admin with 'Change Group Info' permission can remove a channel ID.")
        return

    # Get the channel ID to remove
    channel_id_to_remove = int(event.pattern_match.group(1))

    # Remove the channel from the group's list in MongoDB
    collection.update_one(
        {"group_id": group_id},
        {"$pull": {"channels": channel_id_to_remove}}
    )

    await event.respond(f"Channel ID {channel_id_to_remove} has been removed from the bot.")

# Event handler for new messages in the group
@bot.on(events.NewMessage(incoming=True, func=lambda e: not e.is_private))
async def handler(event):
    print(event.is_channel)
    user_entity = await event.get_sender()

    group_id = event.chat_id
    user_id = event.sender_id

    # Fetch the group's channel data from MongoDB
    group_data = collection.find_one({"group_id": group_id})
    if not group_data or "channels" not in group_data:
        return  # No channels set, ignore messages

    # Fetch user info to check if they are an admin
    user_permissions = await bot.get_permissions(group_id, user_id)

    # Check if the bot has permission to delete messages
    bot_permissions = await bot.get_permissions(group_id, bot._self_id)
    if not bot_permissions.delete_messages:
        # Remove all channel IDs from this group if bot can't delete messages
        collection.update_one({"group_id": group_id}, {"$unset": {"channels": ""}})
        await event.respond("The bot no longer has 'Delete Messages' permission. All channel IDs have been removed.")
        return

    # Check if the sender is not an admin
    if not user_permissions.is_admin or not user_permissions.anonymous:
        for channel_id in group_data["channels"]:
            try:
                # Check if the sender is in the channel
                await bot.get_permissions(channel_id, user_id)
            except telethon.errors.rpcerrorlist.UserNotParticipantError:
                # User is not in the channel, delete their message and send join button
                await event.delete()

                # Get the invite link dynamically
                invite_link = await bot(ExportChatInviteRequest(channel_id))
                user_mention = f"[chutiya](tg://user?id={user_id})"
                join_button = [[Button.url("Join Channel", invite_link.link)]]
                await event.respond(
                    f"{user_mention}, You need to join the channel to send messages here.",
                    buttons=join_button
                )
                break  # No need to check other channels after deleting the message

            except ChatAdminRequiredError:
                # If bot can't check the channel, remove that channel from the group
                collection.update_one({"group_id": group_id}, {"$pull": {"channels": channel_id}})
                await event.respond(f"Bot lost permission to check channel {channel_id}. It has been removed from the list.")
                break

# Start the bot
if __name__ == '__main__':
    print("started")
    bot.run_until_disconnected()
