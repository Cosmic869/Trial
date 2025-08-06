import discord
from discord.ext import commands
from discord.ui import Button, View
import json
import os
import logging
import asyncio
from discord import app_commands
import random

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler('discord_bot.log'),
              logging.StreamHandler()])
logger = logging.getLogger(__name__)

# Load configuration with error handling
try:
    with open('config.json', 'r') as f:
        config = json.load(f)
    logger.info("Configuration loaded successfully")
except FileNotFoundError:
    logger.error(
        "config.json file not found. Please create it with the required settings."
    )
    exit(1)
except json.JSONDecodeError as e:
    logger.error(f"Error parsing config.json: {e}")
    exit(1)
    
# Validate required config keys
required_keys = [
    'min_account_age_days', 'review_channel_id', 'verified_role_id'
]
missing_keys = [key for key in required_keys if key not in config]
if missing_keys:
    logger.error(f"Missing required configuration keys: {missing_keys}")
    exit(1)

intents = discord.Intents.default()
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

verify_button_id = "nsfw_verify_button"

@bot.tree.command(name="setstatus", description="Change the bot's activity status.") 
@app_commands.describe(
    activity_type="Choose activity type: playing, listening, watching, competing",
    status_message="What should the status message be?"
)
async def setstatus(interaction: discord.Interaction, activity_type: str, status_message: str):
    activity_type = activity_type.lower()

    activity_types = {
        "playing": discord.ActivityType.playing,
        "listening": discord.ActivityType.listening,
        "watching": discord.ActivityType.watching,
        "competing": discord.ActivityType.competing
    }

    if activity_type not in activity_types:
        await interaction.response.send_message("Invalid activity type! Choose: playing, listening, watching, competing.", ephemeral=True)
        return

    activity = discord.Activity(type=activity_types[activity_type], name=status_message)
    await bot.change_presence(activity=activity)

    await interaction.response.send_message(f"Status updated to **{activity_type.capitalize()} {status_message}** ✅", ephemeral=True)


@bot.event
async def on_ready():
    logger.info(f'Bot logged in as {bot.user} (ID: {bot.user.id})')
    logger.info(f'Bot is in {len(bot.guilds)} guilds')

    # Sync slash commands on startup
    try:
        synced = await bot.tree.sync()
        logger.info(f'Synced {len(synced)} slash commands')
    except Exception as e:
        logger.error(f'Failed to sync slash commands: {e}')


async def create_verification_embed():
    """Create the verification embed and view"""
    embed = discord.Embed(
        title="🔞 NSFW Verification Required",
        description=
        "To access NSFW sections, click the button below to verify your age and consent.\n\n"
        "**Requirements:**\n"
        f"• Account must be at least {config['min_account_age_days']} days old\n"
        "• Must be 18+ years old\n"
        "• Age verification screenshot (optional)",
        color=0xff69b4)
    embed.set_footer(
        text="This verification process is required for legal compliance.")

    view = View(timeout=None)  # Persistent view
    view.add_item(
        Button(label="🔞 Verify Me",
               style=discord.ButtonStyle.primary,
               custom_id=verify_button_id))

    return embed, view


@bot.command()
async def postverify(ctx):
    """Post the NSFW verification embed with button (prefix command)"""
    try:
        embed, view = await create_verification_embed()
        await ctx.send(embed=embed, view=view)
        logger.info(
            f"Verification embed posted by {ctx.author} in {ctx.channel} (prefix command)"
        )

    except Exception as e:
        logger.error(f"Error posting verification embed: {e}")
        await ctx.send(
            "An error occurred while posting the verification embed.")


# Slash Commands
@bot.tree.command(name="postverify",
                  description="Post the NSFW verification embed with button")
@discord.app_commands.describe()
async def slash_postverify(interaction: discord.Interaction):
    """Post the NSFW verification embed with button (slash command)"""
    try:
        embed, view = await create_verification_embed()
        await interaction.response.send_message(embed=embed, view=view)
        logger.info(
            f"Verification embed posted by {interaction.user} in {interaction.channel} (slash command)"
        )

    except Exception as e:
        logger.error(f"Error posting verification embed: {e}")
        await interaction.response.send_message(
            "An error occurred while posting the verification embed.",
            ephemeral=True)


@bot.tree.command(name="botstats",
                  description="Show bot statistics and health information")
async def slash_botstats(interaction: discord.Interaction):
    """Show bot statistics"""
    try:
        uptime = discord.utils.utcnow() - bot.user.created_at

        embed = discord.Embed(title="🤖 Bot Statistics",
                              color=0x00ff00,
                              timestamp=discord.utils.utcnow())

        embed.add_field(name="🏓 Latency",
                        value=f"{round(bot.latency * 1000)}ms",
                        inline=True)
        embed.add_field(name="🏠 Servers",
                        value=str(len(bot.guilds)),
                        inline=True)
        embed.add_field(name="👥 Users", value=str(len(bot.users)), inline=True)
        embed.add_field(name="⏰ Bot Created",
                        value=bot.user.created_at.strftime("%Y-%m-%d"),
                        inline=True)
        embed.add_field(name="🔧 Commands",
                        value="Prefix: `!` | Slash: `/`",
                        inline=True)
        embed.add_field(name="📊 Status", value="🟢 Online", inline=True)

        embed.set_thumbnail(url=bot.user.display_avatar.url)
        embed.set_footer(text=f"Bot ID: {bot.user.id}")

        await interaction.response.send_message(embed=embed, ephemeral=True)
        logger.info(f"Bot stats requested by {interaction.user}")

    except Exception as e:
        logger.error(f"Error showing bot stats: {e}")
        await interaction.response.send_message(
            "An error occurred while fetching bot statistics.", ephemeral=True)


@bot.tree.command(name="help",
                  description="Show available commands and bot information")
async def slash_help(interaction: discord.Interaction):
    """Show help information"""
    try:
        embed = discord.Embed(
            title="🆘 Bot Help & Commands",
            description=
            "Here are all available commands for this NSFW verification bot:",
            color=0x3498db)

        embed.add_field(name="🔞 Verification Commands",
                        value="`/postverify` - Post the verification embed\n"
                        "`!postverify` - Same as above (prefix version)",
                        inline=False)

        embed.add_field(name="📊 Information Commands",
                        value="`/botstats` - Show bot statistics\n"
                        "`/help` - Show this help message\n"
                        "`/ping` - Check bot response time",
                        inline=False)

        embed.add_field(name="🔧 How Verification Works",
                        value="1. Click the 🔞 Verify Me button\n"
                        "2. Complete the DM questionnaire\n"
                        "3. Upload age verification screenshot (optional)\n"
                        "4. Wait for moderator approval\n"
                        "5. Get notified of the result",
                        inline=False)

        embed.add_field(
            name="⚙️ Configuration",
            value=
            f"• Minimum account age: {config['min_account_age_days']} days\n"
            "• Age requirement: 18+ years\n"
            "• Verification method: Screenshot optional",
            inline=False)

        embed.set_footer(text="Need help? Contact a server administrator")

        await interaction.response.send_message(embed=embed, ephemeral=True)
        logger.info(f"Help requested by {interaction.user}")

    except Exception as e:
        logger.error(f"Error showing help: {e}")
        await interaction.response.send_message(
            "An error occurred while showing help.", ephemeral=True)


@bot.tree.command(name="ping", description="Check bot response time")
async def slash_ping(interaction: discord.Interaction):
    """Check bot latency"""
    try:
        latency = round(bot.latency * 1000)

        if latency < 100:
            status = "🟢 Excellent"
            color = 0x00ff00
        elif latency < 200:
            status = "🟡 Good"
            color = 0xffff00
        else:
            status = "🔴 Poor"
            color = 0xff0000

        embed = discord.Embed(
            title="🏓 Pong!",
            description=f"**Latency:** {latency}ms\n**Status:** {status}",
            color=color)

        await interaction.response.send_message(embed=embed, ephemeral=True)
        logger.info(f"Ping command used by {interaction.user} - {latency}ms")

    except Exception as e:
        logger.error(f"Error with ping command: {e}")
        await interaction.response.send_message(
            "An error occurred while checking ping.", ephemeral=True)


# Admin-only slash commands
@bot.tree.command(name="sync", description="Sync slash commands (Admin only)")
@discord.app_commands.describe()
async def slash_sync(interaction: discord.Interaction):
    """Sync slash commands - Admin only"""
    try:
        # Check if user has administrator permissions
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message(
                "❌ You need Administrator permissions to use this command.",
                ephemeral=True)
            return

        synced = await bot.tree.sync()
        await interaction.response.send_message(
            f"✅ Synced {len(synced)} slash commands!", ephemeral=True)
        logger.info(
            f"Slash commands synced by {interaction.user} - {len(synced)} commands"
        )

    except Exception as e:
        logger.error(f"Error syncing commands: {e}")
        await interaction.response.send_message(
            "An error occurred while syncing commands.", ephemeral=True)


@bot.event
async def on_interaction(interaction):
    """Handle all button interactions"""
    if interaction.type != discord.InteractionType.component:
        return

    custom_id = interaction.data.get("custom_id", "")

    try:
        if custom_id == verify_button_id:
            await handle_verification_start(interaction)
        elif custom_id.startswith("approve_"):
            await handle_approval(interaction, custom_id)
        elif custom_id.startswith("reject_"):
            await handle_rejection(interaction, custom_id)
    except Exception as e:
        logger.error(f"Error handling interaction {custom_id}: {e}")
        try:
            await interaction.response.send_message(
                "An error occurred while processing your request. Please try again later.",
                ephemeral=True)
        except:
            pass


async def handle_verification_start(interaction):
    """Handle the initial verification button click"""
    user = interaction.user

    # Anti-alt check
    account_age_days = (discord.utils.utcnow() - user.created_at).days
    if account_age_days < config['min_account_age_days']:
        await interaction.response.send_message(
            f"❌ Your account is too new to verify. Account must be at least {config['min_account_age_days']} days old.\n"
            f"Your account age: {account_age_days} days",
            ephemeral=True)
        logger.info(
            f"Verification denied for {user} - account too new ({account_age_days} days)"
        )
        return

    try:
        # Send initial response
        await interaction.response.send_message(
            "✅ I've sent you a DM with the verification form. Please check your direct messages.",
            ephemeral=True)

        # Start DM verification process
        await user.send(
            "🔞 **NSFW Verification Process**\n\n"
            "Hello! Let's get you verified for NSFW content access.\n"
            "Please answer the following questions honestly and completely.\n"
            "⏰ You have 5 minutes to complete each step.\n\n"
            "**Let's begin:**")

        questions = [
            "**1.** What is your Discord username and ID? (You can copy this: `{}`#{})"
            .format(user.name, user.discriminator),
            "**2.** How old are you? (Must be 18 or older)",
            "**3.** Do you consent to seeing NSFW content? (Type 'Yes' or 'No')",
            "**4.** Have you read and agreed to the server's NSFW rules? (Type 'Yes' or 'No')"
        ]

        answers = []

        # Ask text questions with timeout
        for i, question in enumerate(questions, 1):
            await user.send(f"{question}")

            try:

                def check(m):
                    return (m.author == user
                            and isinstance(m.channel, discord.DMChannel)
                            and len(m.content.strip()) > 0)

                msg = await bot.wait_for('message', timeout=300,
                                         check=check)  # 5 minutes
                answers.append(msg.content.strip())

                # Validate critical answers
                if i == 2:  # Age question
                    try:
                        age = int(msg.content.strip())
                        if age < 18:
                            await user.send(
                                "❌ You must be 18 or older to access NSFW content. Verification cancelled."
                            )
                            logger.info(
                                f"Verification cancelled for {user} - under 18 (claimed age: {age})"
                            )
                            return
                    except ValueError:
                        await user.send(
                            "❌ Please provide a valid age number. Verification cancelled."
                        )
                        logger.info(
                            f"Verification cancelled for {user} - invalid age format"
                        )
                        return
                elif i in [3, 4]:  # Consent questions
                    if msg.content.strip().lower() not in ['yes', 'y']:
                        await user.send(
                            "❌ You must consent and agree to the rules to access NSFW content. Verification cancelled."
                        )
                        logger.info(
                            f"Verification cancelled for {user} - did not consent/agree"
                        )
                        return

                await user.send("✅ Answer recorded.")

            except asyncio.TimeoutError:
                await user.send(
                    "⏰ Verification timed out. Please start over by clicking the verification button again."
                )
                logger.info(
                    f"Verification timed out for {user} at question {i}")
                return

        # Ask for screenshot (now optional)
        await user.send(
            "**5.** Please upload a screenshot showing your age verification, or type 'skip' to proceed without one.\n"
            "This could be:\n"
            "• Government ID (blur out sensitive info, keep age/DOB visible)\n"
            "• Birth certificate (blur sensitive info)\n"
            "• Any official document showing your date of birth\n\n"
            "**Important:** Blur out all personal information except your age/date of birth.\n"
            "**Note:** You can type 'skip' if you prefer not to upload a screenshot."
        )

        image_url = None
        try:

            def check_image_or_skip(m):
                return (m.author == user
                        and isinstance(m.channel, discord.DMChannel)
                        and (len(m.attachments) > 0
                             or m.content.strip().lower() in ['skip', 's']))

            img_msg = await bot.wait_for('message',
                                         timeout=600,
                                         check=check_image_or_skip
                                         )  # 10 minutes for upload

            if img_msg.content.strip().lower() in ['skip', 's']:
                image_url = "No screenshot provided (skipped by user)"
                await user.send(
                    "✅ Screenshot skipped. Proceeding with verification.")
            else:
                image_url = img_msg.attachments[0].url
                await user.send("✅ Screenshot received.")

        except asyncio.TimeoutError:
            await user.send(
                "⏰ Image upload timed out. Please start over by clicking the verification button again."
            )
            logger.info(f"Image upload timed out for {user}")
            return

        # Send to review channel
        guild = interaction.guild
        review_channel_id = config['review_channel_id']

        if review_channel_id == "REPLACE_WITH_YOUR_REVIEW_CHANNEL_ID":
            await user.send(
                "❌ Bot configuration error. Please contact an administrator.")
            logger.error("Review channel ID not configured properly")
            return

        # Extract actual ID from mention format if needed
        clean_channel_id = extract_id(review_channel_id)
        vr_channel = guild.get_channel(int(clean_channel_id))
        if vr_channel is None:
            await user.send(
                "❌ Review channel not found. Please contact an administrator.")
            logger.error(
                f"Review channel {review_channel_id} not found or bot lacks access"
            )
            return

        # Create review embed
        review_embed = discord.Embed(title="🔞 NSFW Verification Request",
                                     color=0xffa500,
                                     timestamp=discord.utils.utcnow())
        review_embed.add_field(name="👤 User",
                               value=f"{user.mention} ({user})",
                               inline=False)
        review_embed.add_field(name="🆔 Username & ID",
                               value=answers[0],
                               inline=False)
        review_embed.add_field(name="🎂 Age", value=answers[1], inline=True)
        review_embed.add_field(name="✅ Consent", value=answers[2], inline=True)
        review_embed.add_field(name="📜 Agreed to Rules",
                               value=answers[3],
                               inline=True)
        review_embed.add_field(name="📅 Account Created",
                               value=user.created_at.strftime("%Y-%m-%d"),
                               inline=True)
        review_embed.add_field(name="⏰ Account Age",
                               value=f"{account_age_days} days",
                               inline=True)
        review_embed.add_field(name="🖼️ Age Verification",
                               value=f"[View Screenshot]({image_url})",
                               inline=False)
        review_embed.set_thumbnail(url=user.display_avatar.url)

        view = View(timeout=None)
        view.add_item(
            Button(label="✅ Approve",
                   style=discord.ButtonStyle.success,
                   custom_id=f"approve_{user.id}"))
        view.add_item(
            Button(label="❌ Reject",
                   style=discord.ButtonStyle.danger,
                   custom_id=f"reject_{user.id}"))

        await vr_channel.send(embed=review_embed, view=view)
        await user.send(
            "✅ **Verification submitted successfully!**\n\n"
            "Your verification request has been sent to the moderation team for review.\n"
            "You will receive a DM with the result once it's processed.\n\n"
            "Thank you for your patience! 🙏")

        logger.info(f"Verification request submitted for {user}")

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I couldn't send you a DM. Please:\n"
            "1. Enable DMs from server members\n"
            "2. Make sure you haven't blocked the bot\n"
            "3. Try again after adjusting your privacy settings",
            ephemeral=True)
        logger.info(f"Could not DM {user} for verification")
    except Exception as e:
        logger.error(f"Error in verification process for {user}: {e}")
        await user.send(
            "❌ An error occurred during verification. Please try again or contact an administrator."
        )


def extract_id(id_string):
    """Extract ID from mention format or return as-is if already an ID"""
    if isinstance(id_string, str):
        # Remove role mention format <@&123456789> -> 123456789
        if id_string.startswith('<@&') and id_string.endswith('>'):
            return id_string[3:-1]
        # Remove channel mention format <#123456789> -> 123456789
        elif id_string.startswith('<#') and id_string.endswith('>'):
            return id_string[2:-1]
        # Remove user mention format <@123456789> -> 123456789
        elif id_string.startswith('<@') and id_string.endswith('>'):
            return id_string[2:-1]
    return str(id_string)


async def handle_approval(interaction, custom_id):
    """Handle verification approval"""
    user_id = int(custom_id.split("_")[1])
    guild = interaction.guild
    user = guild.get_member(user_id)

    if not user:
        await interaction.response.send_message("❌ User not found in server.",
                                                ephemeral=True)
        return

    verified_role_id = config['verified_role_id']
    if verified_role_id == "REPLACE_WITH_YOUR_VERIFIED_ROLE_ID":
        await interaction.response.send_message(
            "❌ Verified role not configured.", ephemeral=True)
        logger.error("Verified role ID not configured properly")
        return

    # Extract actual ID from mention format if needed
    clean_role_id = extract_id(verified_role_id)
    role = guild.get_role(int(clean_role_id))
    if not role:
        await interaction.response.send_message("❌ Verified role not found.",
                                                ephemeral=True)
        logger.error(f"Verified role {verified_role_id} not found")
        return

    try:
        await user.add_roles(
            role, reason=f"NSFW verification approved by {interaction.user}")
        await interaction.response.send_message(
            f"✅ **Approved** {user.mention} for NSFW access.", ephemeral=True)

        # Update the original message
        embed = interaction.message.embeds[0]
        embed.color = 0x00ff00  # Green
        embed.title = "✅ NSFW Verification - APPROVED"
        embed.add_field(name="📋 Action",
                        value=f"Approved by {interaction.user.mention}",
                        inline=False)

        view = discord.ui.View.from_message(interaction.message)
        for item in view.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

        await interaction.edit_original_response(embed=embed, view=None)

        try:
            await user.send(
                "🎉 **Verification Approved!**\n\n"
                "Congratulations! You have been approved for NSFW access.\n"
                "You can now access all NSFW channels and content in the server.\n\n"
                "Please remember to follow all server rules and guidelines. Enjoy! ✨"
            )
        except discord.Forbidden:
            logger.info(f"Could not DM approval notification to {user}")

        logger.info(
            f"NSFW verification approved for {user} by {interaction.user}")

    except discord.Forbidden:
        await interaction.response.send_message(
            "❌ I don't have permission to assign roles.", ephemeral=True)
        logger.error(f"No permission to assign role to {user}")
    except Exception as e:
        await interaction.response.send_message(
            "❌ An error occurred while approving.", ephemeral=True)
        logger.error(f"Error approving {user}: {e}")


async def handle_rejection(interaction, custom_id):
    """Handle verification rejection"""
    user_id = int(custom_id.split("_")[1])
    guild = interaction.guild
    user = guild.get_member(user_id)

    if not user:
        await interaction.response.send_message("❌ User not found in server.",
                                                ephemeral=True)
        return

    try:
        await interaction.response.send_message(
            f"❌ **Rejected** {user.mention}'s verification request.",
            ephemeral=True)

        # Update the original message
        embed = interaction.message.embeds[0]
        embed.color = 0xff0000  # Red
        embed.title = "❌ NSFW Verification - REJECTED"
        embed.add_field(name="📋 Action",
                        value=f"Rejected by {interaction.user.mention}",
                        inline=False)

        view = discord.ui.View.from_message(interaction.message)
        for item in view.children:
            if isinstance(item, discord.ui.Button):
                item.disabled = True

        await interaction.edit_original_response(embed=embed, view=None)

        try:
            await user.send(
                "❌ **Verification Rejected**\n\n"
                "Unfortunately, your NSFW verification request has been rejected.\n\n"
                "This could be due to:\n"
                "• Insufficient age verification\n"
                "• Incomplete or unclear responses\n"
                "• Not meeting server requirements\n\n"
                "If you believe this was an error, please contact a moderator directly."
            )
        except discord.Forbidden:
            logger.info(f"Could not DM rejection notification to {user}")

        logger.info(
            f"NSFW verification rejected for {user} by {interaction.user}")

    except Exception as e:
        await interaction.response.send_message(
            "❌ An error occurred while rejecting.", ephemeral=True)
        logger.error(f"Error rejecting {user}: {e}")


@bot.event
async def on_error(event, *args, **kwargs):
    """Global error handler"""
    logger.error(f"An error occurred in {event}: {args}, {kwargs}")
    
# Vibecheck Slash Command
@bot.tree.command(name="vibecheck", description="Check your vibe!")
async def vibecheck_slash(interaction: discord.Interaction):
    await vibecheck_logic(interaction)

# Vibecheck Prefix Command
@bot.command(name="vb")
async def vibecheck_prefix(ctx):
    await vibecheck_logic(ctx)

# Shared Logic for Both
async def vibecheck_logic(context):
    vibes = [
        "✅ Vibe Check Passed! You're radiating irresistible energy. 😘",
        "❌ Vibe Check Failed... but you still look cute failing. 😉",
        "🔥 Vibe: Dangerously seductive today. Handle with care.",
        "💋 Vibe: Kissable. Proceed at your own risk.",
        "😈 Vibe: Mischief Mode Activated. Someone's in trouble.",
        "👀 Vibe: Eyes locked. You’re making hearts race.",
        "💖 Vibe: Cuddle magnet. People can’t resist you.",
        "🍑 Vibe: Thick and confident. Show it off!",
        "👄 Vibe: Lips looking... distracting today.",
        "🖤 Vibe: Dark and alluring. Mystery suits you.",
        "🥵 Vibe: You’re too hot. I’m sweating over here.",
        "🛏️ Vibe: Bed’s calling... but for naps. Or is it?",
        "🫦 Vibe: Bite your lip energy. We see you.",
        "💫 Vibe: Flirtatious with a hint of chaos.",
        "👑 Vibe: Dominating the room with that aura.",
        "🥂 Vibe: Toast to your dangerously attractive energy.",
        "🌶️ Vibe: Spicy. You’re playing with fire.",
        "🍒 Vibe: Sweet on the outside, sinful on the inside.",
        "🫣 Vibe: You’ve got people blushing today.",
        "✨ Vibe: You’re the ✨main event✨, as always.",
        "👅 Vibe: Tongue-tied? Or are you making others speechless?",
        "🎀 Vibe: Soft, cute, but secretly corrupting minds.",
        "🫦 Vibe: That smirk should be illegal.",
        "🍓 Vibe: Strawberries and sin, that’s your brand.",
        "📵 Vibe: Too hot to post. The internet can’t handle you.",
        "🎧 Vibe: Listening to “Eargasmic” beats. You naughty lil thing."
    ]

    response = random.choice(vibes)
    if isinstance(context, discord.Interaction):
        await context.response.send_message(response)
    else:
        await context.send(response)

class SayView(View):  # Define the SayView class
    def __init__(self):
        super().__init__()


@bot.tree.command(name="say", description="Make the bot say something!") 
@app_commands.describe(message="What should I say?")
async def say_slash(interaction: discord.Interaction, message: str):
    await interaction.response.send_message(message, view=SayView())

@bot.command(name="say")
async def say_prefix(ctx, *, message: str):
    await ctx.send(message, view=SayView())

@bot.command()
async def hornymeter(ctx):
    level = random.randint(0, 100)
    bar = "█" * (level // 10) + "░" * (10 - (level // 10))
    embed = discord.Embed(
        title="🔞 HornyMeter Results 🔞",
        description=f"{ctx.author.mention}, your **HornyMeter** reads:\n`{bar}` **{level}%**",
        color=discord.Color.pink()
    )
    embed.set_footer(text="Stay hydrated, cutie~ 💦")
    await ctx.send(embed=embed)

@bot.tree.command(name="hornymeter", description="Check your HornyMeter level")
async def slash_hornymeter(interaction: discord.Interaction):
    level = random.randint(0, 100)
    bar = "█" * (level // 10) + "░" * (10 - (level // 10))
    embed = discord.Embed(
        title="🔞 HornyMeter Results 🔞",
        description=f"{interaction.user.mention}, your **HornyMeter** reads:\n`{bar}` **{level}%**",
        color=discord.Color.pink()
    )
    embed.set_footer(text="Stay hydrated, cutie~ 💦")
    await interaction.response.send_message(embed=embed)

moan_battle_images = [
    "https://media.tenor.com/kiss-tease.gif",
    "https://media.tenor.com/moaning-loop.gif",
    "https://media.tenor.com/blush-squirm.gif",
    "https://media.tenor.com/biting-lip.gif",
    "https://cdn.discordapp.com/attachments/1234567890/leaning-close.gif",
    "https://media.tenor.com/soft-moan.gif",
    "https://cdn.discordapp.com/attachments/1234567890/moan-challenge.gif",
    "https://media.tenor.com/ear-bite.gif",
    "https://media.tenor.com/glance-and-blush.gif",
    "https://cdn.discordapp.com/attachments/1234567890/mouth-open-tease.gif",
    "https://media.tenor.com/you-want-more.gif",
    "https://cdn.discordapp.com/attachments/1234567890/playing-with-lips.gif",
    "https://media.tenor.com/moan-in-your-ear.gif",
    "https://media.tenor.com/neck-touch.gif",
    "https://cdn.discordapp.com/attachments/1234567890/tension-stare.gif",
    "https://media.tenor.com/lean-forward-slowly.gif",
    "https://cdn.discordapp.com/attachments/1234567890/squirming-cute.gif",
    "https://media.tenor.com/tease-hands.gif",
    "https://cdn.discordapp.com/attachments/1234567890/come-closer.gif",
    "https://media.tenor.com/too-loud-moan.gif",
    "https://media.tenor.com/headtilt-blush.gif",
    "https://cdn.discordapp.com/attachments/1234567890/sassy-stare.gif",
    "https://media.tenor.com/biting-finger.gif",
    "https://media.tenor.com/lean-and-smirk.gif",
    "https://cdn.discordapp.com/attachments/1234567890/glare-downbad.gif",
    "https://media.tenor.com/knees-weak.gif",
    "https://cdn.discordapp.com/attachments/1234567890/sensual-laugh.gif",
    "https://media.tenor.com/hands-on-chest.gif",
    "https://media.tenor.com/slide-close.gif",
    "https://cdn.discordapp.com/attachments/1234567890/shiver-moan.gif",
    "https://media.tenor.com/come-play-look.gif",
    "https://cdn.discordapp.com/attachments/1234567890/soft-sigh.gif",
    "https://media.tenor.com/that-was-good.gif",
    "https://media.tenor.com/lip-bite-stare.gif",
    "https://cdn.discordapp.com/attachments/1234567890/soft-giggle.gif",
    "https://media.tenor.com/moaning-shake.gif",
    "https://cdn.discordapp.com/attachments/1234567890/eyes-closed-lean.gif",
    "https://media.tenor.com/seducing-you.gif",
    "https://cdn.discordapp.com/attachments/1234567890/lean-in-intense.gif",
    "https://media.tenor.com/low-tone-moan.gif",
    "https://cdn.discordapp.com/attachments/1234567890/arch-back.gif",
    "https://media.tenor.com/downbad-moan.gif",
    "https://cdn.discordapp.com/attachments/1234567890/close-whisper.gif",
    "https://media.tenor.com/softly-whimper.gif",
    "https://cdn.discordapp.com/attachments/1234567890/weak-knees.gif",
    "https://media.tenor.com/flushed-face.gif",
    "https://cdn.discordapp.com/attachments/1234567890/simp-battle.gif",
    "https://media.tenor.com/slow-breathing.gif",
    "https://cdn.discordapp.com/attachments/1234567890/flirty-wink.gif"
]
moan_battle_outcomes = [
    "🫦 The server falls dead silent as {user1} leans in, letting out a slow, sultry moan. {user2} responds by grabbing the mic and delivering a moan so intense the VC nearly explodes. **Round 1? Tied—but the heat is just starting.**",
    "🔥 {user1} starts with a playful giggle, escalating into a soft moan that leaves {user2} flustered. But {user2} smirks, steps forward, and moans with such dominance that even the chat mods are blushing. **The battle is heating up!**",
    "🍑 The tension is unbearable. {user1} whispers a moan into {user2}'s ear, causing them to shiver. Not to be outdone, {user2} locks eyes and moans back—louder, deeper, sinful. **It’s anyone’s game now.**",
    "{user1} teases with a breathy, shaky moan that melts the VC. {user2} counters with a growl-like moan, taking over the entire room. **Victory? Still undecided.**",
    "💦 {user1} leans back, moaning softly, eyes half-lidded. {user2} suddenly steps in, moaning with enough passion to shut the entire VC down. **That was close.**",
    "🔥 The moans escalate back and forth until {user1} lets out a long, drawn-out moan that has everyone flustered. But {user2} chuckles and delivers a fatal blow—a moan so sinful, the VC crashes. **This isn’t over.**",
    "🫦 {user1} starts soft, almost innocent, but {user2} cuts through with a raw, deep moan that shakes the air. **Tensions through the roof!**",
    "{user1} slowly builds their moan, making everyone wait... wait... until it bursts out, full volume. {user2}, however, is unbothered—moaning back with a breathless edge that silences the server. **Absolute chaos.**",
    "🍑 It begins with teasing glances. {user1} moans, drawing in all attention, but {user2} flips the mood with a dangerously seductive moan. **Chat is DOWN BAD.**",
    "💦 {user1} and {user2} are now locked in an endless moaning loop, each one upping the intensity until the entire server is a flustered mess. **No clear winner. Only sinners.**",
    "🔥 {user1} surprises everyone with a sudden, loud moan. {user2} pauses, smiles, and responds with a softer—but way hotter—moan that turns the tables. **Round two incoming!**",
    "{user1} moans into their mic, voice trembling. {user2} steps up, moans back, and the clash is so intense that mods consider muting them both. **But they don’t. They want more.**",
    "🫦 {user1} closes their eyes, breathing deeply before moaning softly. {user2} immediately responds with a playful, high-pitched moan that sends chat into meltdown. **No one's safe.**",
    "{user1} tries to play it cool, but {user2} moans in such a teasing tone that {user1} breaks character, blushing and laughing. **Battle continues.**",
    "🔥 {user1} leans in, whispers a moan that’s barely audible, but it's enough to fluster {user2}. They retaliate by moaning directly into the mic—sending shockwaves across the VC. **The war is ON.**",
    "🍑 A soft, breathy moan from {user1} is answered by a dominant, growling moan from {user2}. **It’s a fight of tones now.**",
    "💦 {user1} tilts their head back, moaning with a shaky breath. {user2} is unfazed, letting out a perfectly controlled moan that asserts full dominance. **Scoreboard’s on FIRE.**",
    "{user1} delivers a moan that sounds like a desperate plea. {user2} responds by turning the mood sensual, moaning so effortlessly that the entire server is down bad. **Who will break first?**",
    "🫦 The air is thick as {user1} moans sweetly, almost shy. {user2} chuckles and unleashes a loud, shameless moan. **Chat is going wild.**",
    "{user1} surprises {user2} with an unexpected moan attack. But {user2} recovers, smirking, and delivers a moan that absolutely crushes any resistance. **Victory? Still up for grabs.**"
]

moan_battle_actions = [
    "{user1} leans in with a teasing moan.",
    "{user2} smirks and moans back seductively.",
    "{user1} bites their lip, releasing a desperate whimper.",
    "{user2} pulls {user1} closer, whispering a sultry moan.",
    "{user1} runs their fingers down {user2}'s spine, making them shiver.",
    "{user2} responds with a playful nibble on {user1}'s ear.",
    "{user1} gasps loudly, their voice trembling.",
    "{user2} grins mischievously and lets out a deep, resonating moan.",
    "{user1} arches their back, releasing a soft, drawn-out moan.",
    "{user2} whispers dirty words into {user1}'s ear, making them blush.",
    "{user1} places a hand on {user2}'s chest, feeling their heartbeat race.",
    "{user2} presses their lips to {user1}'s neck, leaving a faint moan.",
    "{user1} giggles teasingly before letting out a shameless moan.",
    "{user2} grips {user1}'s waist, pulling them into a heated embrace.",
    "{user1} moans breathlessly, locking eyes with {user2}.",
    "{user2} responds by tracing their fingers along {user1}'s jawline.",
    "{user1} leans back, giving a sultry smirk as they moan provocatively.",
    "{user2} brushes their lips against {user1}'s, sending a wave of tension.",
    "{user1} gasps as {user2} pulls them closer by the collar.",
    "{user2} lets out a victorious moan, claiming dominance in the battle."
 ]

@bot.tree.command(name="moanbattle", description="Challenge someone to a Moan Battle RP style.")
@app_commands.describe(user="Who are you moan battling?")
async def slash_moanbattle(interaction: discord.Interaction, user: discord.Member):
    user1 = interaction.user.mention
    user2 = user.mention
    rounds = random.randint(3, 6)
    battle_log = ""
    for i in range(rounds):
        action = random.choice(moan_battle_actions).format(user1=user1, user2=user2)
        battle_log += f"Round {i+1}: {action}\n"
    finisher_moves = [
        "{winner} unleashes a final, devastating moan that echoes through the VC, leaving {loser} speechless.",
        "{winner} whispers the naughtiest words into {loser}'s ear, sealing their victory with a shiver.",
        "{winner} leans in for a victorious smirk, while {loser} admits defeat with a blush.",
        "{winner} pins {loser} down with an irresistible final move, claiming dominance in the most dramatic way."
    ]
    winner = random.choice([user1, user2])
    loser = user2 if winner == user1 else user1
    finisher = random.choice(finisher_moves).format(winner=winner, loser=loser)
    outcome = f"FinalOutcome:{finisher}"
    image = random.choice(moan_battle_images)
    embed = discord.Embed(title="\U0001F3A4 Moan Battle RP Showdown!", description=battle_log + outcome, color=discord.Color.pink())
    embed.set_image(url=image)
    await interaction.response.send_message(embed=embed)
   
@bot.command(name="mb")
async def moanbattle_prefix(ctx, user: discord.Member):
    user1 = ctx.author.mention
    user2 = user.mention
    rounds = random.randint(3, 6)
    battle_log = ""
    for i in range(rounds):
        action = random.choice(moan_battle_actions).format(user1=user1, user2=user2)
        battle_log += f"Round {i+1}: {action}\n"
    outcome = f"\n**Final Outcome:** {random.choice([user1, user2])} wins the moan battle, leaving everyone flustered!"
    image = random.choice(moan_battle_images)
    embed = discord.Embed(title="\U0001F3A4 Moan Battle RP Showdown!", description=battle_log + outcome, color=discord.Color.pink())
    embed.set_image(url=image)
    await ctx.send(embed=embed)

@moanbattle_prefix.error
async def moanbattle_error(ctx, error):
    if isinstance(error, commands.MissingRequiredArgument):
        await ctx.send("You need to mention a user for the moan battle!")
        
@bot.tree.command(name="simpfor", description="Declare who you're simping for!")
@app_commands.describe(user="The lucky person you're simping for")
async def slash_simpfor(interaction: discord.Interaction, user: discord.Member):
    reactions = [
        f"{interaction.user.mention} is now **officially SIMPING HARD** for {user.mention}!",
        f"{interaction.user.mention} couldn't resist and is **down bad** for {user.mention}!",
        f"{interaction.user.mention} is now {user.mention}'s **certified simp**!",
        f"{interaction.user.mention} just confessed their simping for {user.mention}!",
        f"📢 Everyone! {interaction.user.mention} is now **SIMPING FULL-TIME** for {user.mention}!"
    ]
    bonus_flirts = [
        f"{user.mention}, give {interaction.user.mention} a headpat for their loyalty~ 🥺",
        f"{user.mention}, will you accept {interaction.user.mention} as your humble simp servant? 🍓",
        f"{user.mention}, looks like you have a personal fanclub now~ ✨",
        f"{user.mention}, someone's blushing HARD after this announcement~ 💦"
    ]

    embed = discord.Embed(
        title="💖 Simp Declaration! 💖",
        description=f"{random.choice(reactions)}\n\n{random.choice(bonus_flirts)}",
        color=discord.Color.magenta()
    )
    embed.set_thumbnail(url=interaction.user.avatar.url)
    embed.set_footer(text="Certified Down Bad 🫦")

    await interaction.response.send_message(embed=embed)

@bot.command()
async def simpfor(ctx, user: discord.Member):
    reactions = [
        f"{ctx.author.mention} is now **officially SIMPING HARD** for {user.mention}!",
        f"{ctx.author.mention} couldn't resist and is **down bad** for {user.mention}!",
        f"{ctx.author.mention} is now {user.mention}'s **certified simp**!",
        f"{ctx.author.mention} just confessed their simping for {user.mention}!",
        f"📢 Everyone! {ctx.author.mention} is now **SIMPING FULL-TIME** for {user.mention}!"
    ]
    bonus_flirts = [
        f"{user.mention}, give {ctx.author.mention} a headpat for their loyalty~ 🥺",
        f"{user.mention}, will you accept {ctx.author.mention} as your humble simp servant? 🍓",
        f"{user.mention}, looks like you have a personal fanclub now~ ✨",
        f"{user.mention}, someone's blushing HARD after this announcement~ 💦"
    ]

    embed = discord.Embed(
        title="💖 Simp Declaration! 💖",
        description=f"{random.choice(reactions)}\n\n{random.choice(bonus_flirts)}",
        color=discord.Color.magenta()
    )
    embed.set_thumbnail(url=ctx.author.avatar.url)
    embed.set_footer(text="Certified Down Bad 🫦")

    await ctx.send(embed=embed)

sex_battle_images = [
    "https://media.tenor.com/teasing-dance.gif",
    "https://media.tenor.com/sensual-touch.gif",
    "https://cdn.discordapp.com/attachments/1234567890/bed-grab.gif",
    "https://media.tenor.com/slowly-undressing.gif",
    "https://media.tenor.com/whisper-in-ear.gif",
    "https://cdn.discordapp.com/attachments/1234567890/lap-sit.gif",
    "https://media.tenor.com/close-body-grind.gif",
    "https://cdn.discordapp.com/attachments/1234567890/straddle.gif",
    "https://media.tenor.com/eye-contact-game.gif",
    "https://media.tenor.com/grab-collar.gif",
    "https://cdn.discordapp.com/attachments/1234567890/wall-pin.gif",
    "https://media.tenor.com/soft-massage.gif",
    "https://cdn.discordapp.com/attachments/1234567890/neck-kiss.gif",
    "https://media.tenor.com/fingers-locked.gif",
    "https://media.tenor.com/pull-you-closer.gif",
    "https://cdn.discordapp.com/attachments/1234567890/bed-push.gif",
    "https://media.tenor.com/sensual-slow-dance.gif",
    "https://cdn.discordapp.com/attachments/1234567890/hips-grab.gif",
    "https://media.tenor.com/body-roll.gif",
    "https://cdn.discordapp.com/attachments/1234567890/back-arch-pull.gif",
    "https://media.tenor.com/eye-roll-tease.gif",
    "https://cdn.discordapp.com/attachments/1234567890/rough-hair-pull.gif",
    "https://media.tenor.com/cuddle-pounce.gif",
    "https://cdn.discordapp.com/attachments/1234567890/collar-tug.gif",
    "https://media.tenor.com/breathless-moment.gif",
    "https://cdn.discordapp.com/attachments/1234567890/hand-guided.gif",
    "https://media.tenor.com/lip-glance-down.gif",
    "https://cdn.discordapp.com/attachments/1234567890/steamy-breath.gif",
    "https://media.tenor.com/edge-kiss.gif",
    "https://cdn.discordapp.com/attachments/1234567890/fingers-tease.gif",
    "https://media.tenor.com/ride-you-energy.gif",
    "https://cdn.discordapp.com/attachments/1234567890/soft-bed-fall.gif",
    "https://media.tenor.com/soft-grind.gif",
    "https://cdn.discordapp.com/attachments/1234567890/bed-play.gif",
    "https://media.tenor.com/close-forehead-touch.gif",
    "https://cdn.discordapp.com/attachments/1234567890/firm-hold.gif",
    "https://media.tenor.com/neck-grab-light.gif",
    "https://cdn.discordapp.com/attachments/1234567890/legs-wrap.gif",
    "https://media.tenor.com/bite-shoulder.gif",
    "https://cdn.discordapp.com/attachments/1234567890/kiss-down-neck.gif",
    "https://media.tenor.com/hips-on-hands.gif",
    "https://cdn.discordapp.com/attachments/1234567890/pin-to-bed.gif",
    "https://media.tenor.com/push-you-down.gif",
    "https://cdn.discordapp.com/attachments/1234567890/whisper-slow.gif",
    "https://media.tenor.com/glance-as-you-drop.gif",
    "https://cdn.discordapp.com/attachments/1234567890/pillow-grab.gif",
    "https://media.tenor.com/pull-on-shirt.gif",
    "https://cdn.discordapp.com/attachments/1234567890/arch-body.gif",
    "https://media.tenor.com/you-asked-for-this.gif"
]
sex_battle_outcomes = [
    "🔥 {user1} initiates with a teasing grind, but {user2} grabs them by the waist, pulling them closer with a dangerous smirk. **Tension skyrockets.**",
    "🫦 {user1} starts slow, seductive, hands tracing soft patterns, but {user2} flips them over in a bold move, asserting dominance. **The battle shifts.**",
    "🍑 {user1} leans in, whispering sinful words, but {user2} responds by pushing them against the wall, staring deep into their eyes. **The server is speechless.**",
    "{user1} grazes their fingers across {user2}'s jawline, but {user2} responds by biting their lip and taking control of the rhythm. **The heat is unreal.**",
    "🔥 {user1} plays innocent, but {user2} pins them down, turning up the intensity until chat is screaming. **It's a massacre.**",
    "🫦 A soft touch from {user1} turns into a passionate exchange of moves, but {user2} smirks and takes over, leading the dance of dominance. **No one is backing down.**",
    "{user1} tries to take charge, but {user2} counters every move with slow, deliberate seduction. **The power shifts.**",
    "🍑 {user1} teases with light brushes of contact, but {user2} retaliates with a commanding grip, forcing the rhythm their way. **Everyone's watching.**",
    "💦 The battle escalates into a full display of sinful choreography, neither {user1} nor {user2} willing to submit. **The tension is suffocating.**",
    "{user1} whispers something filthy, but {user2} answers with actions, not words—pulling them into a flustered mess. **Who’s losing? The chat.**",
    "🔥 {user1} starts with soft, delicate gestures, but {user2} pulls them into their lap, shifting the vibe instantly. **This battle is spicy.**",
    "🫦 The moment {user1} thinks they're in control, {user2} spins them around, taking the lead with a dominating stare. **The tables have turned.**",
    "{user1} leans in for a soft, teasing touch, but {user2} pulls them into a slow grind that has everyone in the chat losing their minds. **Heat level: MAX.**",
    "🍑 {user1} surprises {user2} with a sudden grab, but {user2} smoothly retaliates with a counter that leaves {user1} breathless. **No mercy.**",
    "🔥 {user1} traces their fingers down {user2}'s spine, but {user2} lifts their chin, asserting dominance with a single look. **Server meltdown initiated.**",
    "🫦 Every move {user1} makes is met with an equally bold counter from {user2}. Neither is willing to surrender. **This is a war of wills.**",
    "{user1} tries to seduce with playful nibbles, but {user2} escalates with a sinful grind that leaves the entire VC down bad. **No survivors.**",
    "🍑 The match reaches its peak when {user1} attempts a final, daring move—but {user2} flips the situation with breathtaking precision. **Server can’t handle this.**",
    "🔥 The battle is so intense that mods are considering shutting it down—but everyone’s too invested. {user1} and {user2} have the entire VC on edge. **It’s legendary.**",
    "🫦 As {user1} delivers a final seductive blow, {user2} responds with a victorious smirk, pulling them into a dramatic, show-stopping end. **No one's forgetting this battle.**"
]
sex_battle_actions = [
        "{user1} pins {user2} against the wall, grinding slowly.",
        "{user2} flips {user1} around, taking control.",
        "{user1} drags a finger down {user2}'s chest, smirking.",
        "{user2} retaliates by gripping {user1}'s hips firmly.",
        "{user1} pulls {user2} into a deep, intense kiss.",
        "{user2} whispers something filthy into {user1}'s ear.",
        "{user1} trails kisses along {user2}'s neck, making them gasp.",
        "{user2} bites their lip, pulling {user1} closer with a firm grip.",
        "{user1} traces circles on {user2}'s thigh, teasing mercilessly.",
        "{user2} lifts {user1} up, pressing them against the nearest surface.",
        "{user1} moans softly while gripping {user2}'s shirt.",
        "{user2} trails their fingers up {user1}'s back, making them shiver.",
        "{user1} grazes their teeth along {user2}'s jawline.",
        "{user2} presses their body closer, intensifying the heat.",
        "{user1} runs their hands through {user2}'s hair, tugging gently.",
        "{user2} guides {user1}'s movements with a dominant hold.",
        "{user1} breathes heavily, matching {user2}'s rhythm perfectly.",
        "{user2} pins {user1}'s wrists above their head, taking full control.",
        "{user1} grinds harder, challenging {user2} to keep up.",
        "{user2} smirks and deepens the intensity, overwhelming {user1}."
    ]

@bot.tree.command(name="sexbattle", description="Challenge someone to a spicy RP Sex Battle.")
@app_commands.describe(user="Who are you battling?")
async def slash_sexbattle(interaction: discord.Interaction, user: discord.Member):
    user1 = interaction.user.mention
    user2 = user.mention
    rounds = random.randint(3, 6)
    battle_log = ""
    for i in range(rounds):
        action = random.choice(sex_battle_actions).format(user1=user1, user2=user2)
        battle_log += f"Round {i+1}: {action}\n"
    finisher_moves = [
    "{winner} delivers a breathtaking final grind, overwhelming {loser} completely.",
    "{winner} leans in, whispers something sinful, and watches as {loser} crumbles.",
    "{winner} pulls {loser} into a deep, dominating kiss that leaves no room for resistance.",
    "{winner} finishes with a display of pure control, making {loser} surrender with a flushed smile."
]
    winner = random.choice([user1, user2])
    loser = user2 if winner == user1 else user1
    finisher = random.choice(finisher_moves).format(winner=winner, loser=loser)
    outcome = f"FinalOutcome:** {finisher}"
    image = random.choice(sex_battle_images)
    embed = discord.Embed(title="\U0001F4A5 Sex Battle RP Begins!", description=battle_log + outcome, color=discord.Color.red())
    embed.set_image(url=image)
    await interaction.response.send_message(embed=embed)

@bot.command(name="sb")
async def sexbattle_prefix(ctx, user: discord.Member):
    user1 = ctx.author.mention
    user2 = user.mention
    rounds = random.randint(3, 6)
    battle_log = ""
    for i in range(rounds):
        action = random.choice(sex_battle_actions).format(user1=user1, user2=user2)
        battle_log += f"Round {i+1}: {action}\n"
    outcome = f"\n**Final Outcome:** {random.choice([user1, user2])} dominates the battle, leaving the VC in chaos!"
    image = random.choice(sex_battle_images)
    embed = discord.Embed(title="\U0001F4A5 Sex Battle RP Begins!", description=battle_log + outcome, color=discord.Color.red())
    embed.set_image(url=image)
    await ctx.send(embed=embed)

@bot.tree.command(name="nr", description="Check your naughtiness level!")
async def slash_nr(interaction: discord.Interaction):
    level = random.randint(1, 100)
    if level <= 30:
        color = discord.Color.blue()
        comment = "You're innocent... for now. 👼"
    elif level <= 60:
        color = discord.Color.purple()
        comment = "You're mildly naughty. Potential detected. 👀"
    elif level <= 85:
        color = discord.Color.orange()
        comment = "Certified down-bad energy today. 🔥"
    else:
        color = discord.Color.red()
        comment = "Lewd Energy MAXED OUT. Stay hydrated! 💦"

    embed = discord.Embed(
        title="🫦 Naughtiness Meter 🫦",
        description=f"{interaction.user.mention}, your naughtiness level today is:",
        color=color
    )
    embed.add_field(name="💢 NAUGHTY LEVEL 💢", value=f"**{level}%**", inline=False)
    embed.set_footer(text=comment)
    embed.set_thumbnail(url=interaction.user.avatar.url)

    await interaction.response.send_message(embed=embed)
    
@bot.command()
async def nr(ctx):
    level = random.randint(1, 100)
    if level <= 30:
        color = discord.Color.blue()
        comment = "You're innocent... for now. 👼"
    elif level <= 60:
        color = discord.Color.purple()
        comment = "You're mildly naughty. Potential detected. 👀"
    elif level <= 85:
        color = discord.Color.orange()
        comment = "Certified down-bad energy today. 🔥"
    else:
        color = discord.Color.red()
        comment = "Lewd Energy MAXED OUT. Stay hydrated! 💦"

    embed = discord.Embed(
        title="🫦 Naughtiness Meter 🫦",
        description=f"{ctx.author.mention}, your naughtiness level today is:",
        color=color
    )
    embed.add_field(name="💢 NAUGHTY LEVEL 💢", value=f"**{level}%**", inline=False)
    embed.set_footer(text=comment)
    embed.set_thumbnail(url=ctx.author.avatar.url)

    await ctx.send(embed=embed)

@bot.command(name="setstatus")
@commands.has_permissions(administrator=True)  # Admin Check
async def setstatus(ctx, activity_type: str, *, status_message: str):
    # OPTIONAL: Only allow you (Melisa) to use it by user ID
    allowed_user_id = 636731375831220234  # Replace with your Discord ID (e.g., 123456789012345678)
    if ctx.author.id != allowed_user_id and not ctx.author.guild_permissions.administrator:
        await ctx.send("🚫 You don't have permission to use this command.")
        return

    activity_type = activity_type.lower()

    activity_types = {
        "playing": discord.ActivityType.playing,
        "listening": discord.ActivityType.listening,
        "watching": discord.ActivityType.watching,
        "competing": discord.ActivityType.competing
    }

    if activity_type not in activity_types:
        await ctx.send("❌ Invalid activity type! Use: playing, listening, watching, competing.")
        return

    activity = discord.Activity(type=activity_types[activity_type], name=status_message)
    await bot.change_presence(activity=activity)

    await ctx.send(f"✅ Status updated to **{activity_type.capitalize()} {status_message}**")



from monitor_bot import keep_alive

keep_alive()

# Run the bot
if __name__ == "__main__":
    token = os.environ.get('DISCORD_BOT_TOKEN')
    if not token:
        logger.error("DISCORD_BOT_TOKEN environment variable not set")
        exit(1)

    try:
        bot.run(token)
    except discord.LoginFailure:
        logger.error("Invalid bot token")
    except Exception as e:
        logger.error(f"Failed to start bot: {e}")
