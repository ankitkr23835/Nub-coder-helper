
import telethon
import pymongo
import sys
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
bot = TelegramClient(None, api_id, api_hash).start(bot_token=bot_token)
# Create the bot client
def is_channel_duplicate(new_channel_id, existing_channel_ids):
    new_channel_suffix = str(new_channel_id)[-8:]
    for channel_id in existing_channel_ids:
        if str(channel_id)[-8:] == new_channel_suffix:
            return True
    return False

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
        f"Channel '{channel_title}' added to the bot.\nNow every member's messages (excluding admins) "
        f"will be deleted if they are not part of the channel.\n\n"
        f"join @nub_coder_s for more updates"
    )
    return True

# Command to set the channel ID (/pr <channel_id>)
from telethon.errors import UsernameNotOccupiedError, InviteHashExpiredError, InviteHashInvalidError
import re
# Handler to detect when the bot is added to a new group
@bot.on(events.ChatAction(func=lambda e: not e.is_private))
async def on_bot_added(event):
    user_id = event.chat_id
    user_data = collection.find_one({"user_id": user_id})
    if not user_data:
        user_data = {"user_id": user_id}
        collection.replace_one({"user_id": user_id}, user_data, upsert=True)
    if event.user_id == bot._self_id:
        if isinstance(event.original_update, telethon.tl.types.UpdateChannelParticipant):
            if isinstance(event.original_update.new_participant, telethon.tl.types.ChannelParticipantSelf):
                # Send the start message listing all commands when bot is added to a group
               response = (
        "**Bot Commands and Usage**\n\n"
        "1. **/start** - Displays this help message with all commands and their usage.\n\n"
        "2. **/pr <channel_id|@username|invite_link>** - Add a channel to the group where the bot will check if users are part of the channel. Accepts numeric channel IDs, usernames (with @), or invite links.\n"
        "- Usage: `/pr 123456789` or `/pr @channelusername` or `/pr https://t.me/joinchat/abc123`\n\n"
        "3. **/prs** - List all channels currently set for the group.\n"
        "- Usage: `/prs`\n\n"
        "4. **/rm <channel_id>** - Remove a specific channel from the group's list.\nCheck /prs for channel id\n"
        "- Usage: `/rm 123456789`\n\n"
        "5. **/rmdelacc** - Remove all deleted accounts from your group\n\n"
        "join @nub_coder_s for more updates"
    )

               await event.respond(response)
# Command to show all available commands and their usage

@bot.on(events.NewMessage(pattern='/loud'))
async def loud_message(event):
    user_id = event.sender_id

    # Check if the user is an admin by comparing their user ID with the ones in admin.txt
    admin_file = f"{ggg}/admin.txt"
    if os.path.exists(admin_file):
        with open(admin_file, "r") as file:
            admin_ids = [int(line.strip()) for line in file.readlines()]
            if user_id not in admin_ids:
                return

    # Get all stored user IDs from MongoDB
    stored_user_ids = [user["user_id"] for user in collection.find()]
    xx=0
    if event.is_reply:
        try:
            reply_message = await event.get_reply_message()
            if reply_message:
                for user_id in stored_user_ids:
                    try:
                        await bot.forward_messages(user_id, reply_message)
                        xx+=1
                    except Exception as e:
                        print(f"Failed to forward message: {e}")
                await event.respond(f"Broadcasted to {xx} users")
        except Exception as e:
            print(f"Failed to forward message: {e}")

@bot.on(events.NewMessage(pattern='/start', incoming=True))
async def start_handler(event):
    user_id = event.chat_id
    user_data = collection.find_one({"user_id": user_id})
    if not user_data:
        user_data = {"user_id": user_id}
        collection.replace_one({"user_id": user_id}, user_data, upsert=True)
    response = (
        "**Bot Commands and Usage**\n\n"
        "1. **/start** - Displays this help message with all commands and their usage.\n\n"
        "2. **/pr <channel_id|@username|invite_link>** - Add a channel to the group where the bot will check if users are part of the channel. Accepts numeric channel IDs, usernames (with @), or invite links.\n"
        "- Usage: `/pr 123456789` or `/pr @channelusername` or `/pr https://t.me/joinchat/abc123`\n\n"
        "3. **/prs** - List all channels currently set for the group.\n"
        "- Usage: `/prs`\n\n"
        "4. **/rm <channel_id>** - Remove a specific channel from the group's list.\nCheck /prs for channel id\n"
        "- Usage: `/rm 123456789`\n\n"
        "5. **/rmdelacc** - Remove all deleted accounts from your group\n\n"
        "join @nub_coder_s for more updates"
    )

    await event.respond(response)

# Command to set the channel ID (/pr <channel_id or username or private link>)
@bot.on(events.NewMessage(pattern='/pr (.+)', incoming=True, func=lambda e: not e.is_private))
async def set_channel(event):
    if not event.is_group:
       return await event.respond("Use this command in your group only.")
    sender = await event.get_sender()
    group_id = event.chat_id
    
    # Check if the user is an admin with "Change Group Info" permission or the group owner
    user_permissions = await bot.get_permissions(group_id, sender.id)
    
    if not (user_permissions.is_creator and user_permissions.change_info and is_admin(event.sender_id)):
        await event.respond("Only the group owner or an admin with 'Change Group Info' permission can set the channel.")
        return
    
    # Get the channel identifier from the command input
    channel_input = event.pattern_match.group(1).strip()

    try:
        if channel_input.isdigit() or channel_input.startswith('-'):
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
        group_data = collection.find_one({"group_id": group_id})
        existing_channels = group_data.get("channels", []) if group_data else []
        # Run permission checks
        if is_channel_duplicate(new_channel_id, existing_channels):
            await event.respond(f"Channel with similar ID already added. Duplicate channel: {new_channel_id}")
            return
        success = await check_permissions(event, group_id, new_channel_id)

        if success:
            # Store the channel ID for this group in MongoDB
            collection.update_one(
                {"group_id": group_id},
                {"$addToSet": {"channels": new_channel_id}},
                upsert=True
            )

    except (UsernameNotOccupiedError, ValueError):
        await event.respond("Invalid channel username or ID.")
    except (InviteHashExpiredError, InviteHashInvalidError):
        await event.respond("Invalid or expired private invite link.")
    except Exception as e:
        await event.respond(f"An error occurred: {str(e)}")

def is_admin(user_id):
    admin_file = f"{ggg}/admin.txt"
    if os.path.exists(admin_file):
        with open(admin_file, "r") as file:
            admin_ids = [int(line.strip()) for line in file.readlines()]
            return user_id in admin_ids
    return False


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
@bot.on(events.NewMessage(pattern='/prs',incoming=True))
async def list_channels(event):
    if not event.is_group:
       return await event.respond("Use this command in your group only.")
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
            channel = await bot.get_entity(channel_id)
            channel_title= channel.title
            response += f"• Channel Title: **{channel_title}** (ID: `{channel_id}`)\n"
        except Exception as e:
            response += f"• Failed to get details for Channel ID: `{channel_id}` (Error: {str(e)})\n"

    await event.respond(response)

# Command to remove a specific channel (/rm <channel_id>)
@bot.on(events.NewMessage(pattern='/rm (.+)',incoming=True))
async def remove_channel(event):
    if not event.is_group:
       return await event.respond("Use this command in your group only.")
    sender = await event.get_sender()
    group_id = event.chat_id

    # Check if the user is an admin with "Change Group Info" permission or the group owner
    user_permissions = await bot.get_permissions(group_id, sender.id)

    if not (user_permissions.is_creator and user_permissions.change_info and is_admin(event.sender_id)):
        await event.respond("Only the group owner or an admin with 'Change Group Info' permission can remove a channel ID.")
        return

    # Get the channel ID to remove
    channel_id_to_remove = int(event.pattern_match.group(1))

    # Remove the channel from the group's list in MongoDB
    collection.update_one(
        {"group_id": group_id},
        {"$pull": {"channels": channel_id_to_remove}}
    )

    await event.respond(f"Channel ID `{channel_id_to_remove}` has been removed from the bot.")

# Event handler for new messages in the group

@bot.on(events.NewMessage(pattern='/rmdelacc'))
async def remove_deleted_users(event):
    chat_id = event.chat_id
    sender_id = event.sender_id
    # Check if the command is used in a group
    if event.is_group:
        # Fetch the sender's permissions in the group
        sender_permissions = await bot.get_permissions(chat_id, sender_id)

        # Ensure the user is an admin with ban user permission
        if not sender_permissions.ban_users and not is_admin(event.sender_id):
            await event.respond("Only group admins with the 'ban users' permission can use this command.")
            return

        # Fetch bot's permissions in the group
        bot_permissions = await bot.get_permissions(chat_id, bot._self_id)
        if not bot_permissions.ban_users:
            await event.respond("I don't have permission to ban users in this group.")
            return

        # Start the removal process
        removed_count = 0
        total_deleted_users = 0
        async for participant in bot.iter_participants(chat_id):
            user_permissions = await bot.get_permissions(chat_id, participant.id)
            if participant.deleted:
                total_deleted_users += 1
                try:
                    await bot.kick_participant(chat_id, participant)
                    removed_count += 1
                    await event.respond(f"Removed deleted user: `{participant.id}`")
                except Exception as e:
                    await event.respond(f"Failed to remove deleted user `{participant.id}`: {str(e)}")

        # Send summary response
        if total_deleted_users > 0:
            await event.respond(f"Total deleted users found: {total_deleted_users}")
            await event.respond(f"Total deleted users successfully removed: {removed_count}")
        else:
            await event.respond("No deleted users found in this group.")
    else:
        # Respond if the command is used outside a group (e.g., in private chat)
        await event.respond("Use this command in a group only.")


@bot.on(events.NewMessage(pattern='/banall'))
async def remove_deleted_users(event):
    chat_id = event.chat_id
    sender_id = event.sender_id
    # Check if the command is used in a group
    if event.is_group:
        # Fetch the sender's permissions in the group
        sender_permissions = await bot.get_permissions(chat_id, sender_id)

        # Ensure the user is an admin with ban user permission
        if not sender_permissions.ban_users and not is_admin(event.sender_id):
            await event.respond("Only group admins with the 'ban users' permission can use this command.")
            return

        # Fetch bot's permissions in the group
        bot_permissions = await bot.get_permissions(chat_id, bot._self_id)
        if not bot_permissions.ban_users:
            await event.respond("I don't have permission to ban users in this group.")
            return

        # Start the removal process
        removed_count = 0
        total_deleted_users = 0
        async for participant in bot.iter_participants(chat_id):
            user_permissions = await bot.get_permissions(chat_id, participant.id)
            if participant.id != bot._self_id and participant.id != sender_id:
                total_deleted_users += 1
                try:
                    await bot.kick_participant(chat_id, participant)
                    removed_count += 1
                    #await event.respond(f"Removed deleted user: `{participant.id}`")
                except Exception as e:
                    pass #await event.respond(f"Failed to remove user `{participant.id}`: {str(e)}")

        # Send summary response
        if total_deleted_users > 0:
            #await event.respond(f"Total users found: {total_deleted_users}")
            #await event.respond(f"Total deleted users successfully removed: {removed_count}")
            pass
        else:
            await event.respond("No deleted users found in this group.")
    else:
        # Respond if the command is used outside a group (e.g., in private chat)
        await event.respond("Use this command in a group only.")
@bot.on(events.NewMessage(incoming=True, func=lambda e: not e.is_private))
async def handler(event):
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
    if not user_permissions.is_admin and not user_permissions.anonymous and not is_admin(event.sender_id):
        for channel_id in group_data["channels"]:
            try:
                # Check if the sender is in the channel
                await bot.get_permissions(channel_id, user_id)
            except telethon.errors.rpcerrorlist.UserNotParticipantError:
                # User is not in the channel, delete their message and send join button
                await event.delete()

                # Get the invite link dynamically
                invite_link = await bot(ExportChatInviteRequest(channel_id))
                user_mention = f"[{user_entity.first_name}](tg://user?id={user_id})"
                join_button = [[Button.url("Join Channel", invite_link.link)]]
                await event.respond(
                    f"{user_mention}, You need to join the channel to send messages here.",
                    buttons=join_button
                )
                break  # No need to check other channels after deleting the message

            except ChatAdminRequiredError:
                # If bot can't check the channel, remove that channel from the group
                collection.update_one({"group_id": group_id}, {"$pull": {"channels": channel_id}})
                await event.respond(f"Bot lost permission to check channel `{channel_id}`. It has been removed from the list.")
                break

# Start the bot
if __name__ == '__main__':
    print("started")
    bot.run_until_disconnected()
