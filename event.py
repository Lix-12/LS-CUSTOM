from discord.ext import commands
from collections import defaultdict
import discord
from discord import ui
import json
import os
import re
import datetime

role_direction = "DIRECTION"  # Nom du rôle Direction
role_mention = "Client"


ABSENCE_CHANNEL_ID = 1401923294948626615
SERVICE_LOGS_CHANNEL_ID = 1401917714553110538
SERVICE_GESTION_CHANNEL_ID = 1286393595091226791 #Pour forcer les fins de service
SERVICE_CHANNEL_ID = 1401923160282103838  # ID du salon tu dois mettre la commande '!service' pour mettre les boutons
RECRUTEMENT_CHANNEL_ID = 1380474501665521687  # ID du salon de recrutement
INFO_CHANNEL_ID = 1401922832073490543
ADVERT_CHANNEL_ID = 1401959276313972776
ADVERT_CHANNEL_TARGET_ID = 1401917681191616613

SERVICE_ACTIF_FILE = "service_actif.json"  # Fichier pour sauvegarder les services actifs
FICHIER_EMPLOYES = "employees.json"

user_service_start = defaultdict(lambda: None)
absence_embed_message_id = None
info_embed_message_id = None 
advert_counter = 0  # Compteur global pour les Adverts
recrutement_ouvert = False

def load_active_services():
    """Charge la liste des services actifs depuis le fichier"""
    if not os.path.exists(SERVICE_ACTIF_FILE):
        with open(SERVICE_ACTIF_FILE, "w", encoding="utf-8") as f:
            json.dump({"message_id": None, "message_service": None, "channel_id": None, "channel_service": None, "services": []}, f)
        return {"message_id": None, "channel_id": None, "services": []}
    
    try:
        with open(SERVICE_ACTIF_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        data = {"message_id": None, "message_service": None, "channel_id": None, "channel_service": None, "services": []}
        with open(SERVICE_ACTIF_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        return data

def save_active_services(data):
    """Sauvegarde les services actifs"""
    try:
        with open(SERVICE_ACTIF_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
    except Exception as e:
        print(f"Erreur lors de la sauvegarde des services actifs: {e}")

# 2. Correction des fonctions add_active_service et remove_active_service
def add_active_service(user_id, user_name, start_time, service_type):
    """Ajoute un service actif"""
    try:
        data = load_active_services()
        for service in data["services"]:
            if service["user_id"] == str(user_id):
                service["start_time"] = start_time
                service["service_type"] = service_type
                save_active_services(data)
                return
        
        data["services"].append({
            "user_id": str(user_id),
            "user_name": user_name,
            "start_time": start_time,
            "service_type": service_type
        })
        save_active_services(data)
    except Exception as e:
        print(f"Erreur lors de l'ajout du service actif: {e}")

def remove_active_service(user_id):
    """Supprime un service actif"""
    try:
        data = load_active_services()
        data["services"] = [s for s in data["services"] if s["user_id"] != str(user_id)]
        save_active_services(data)
        return len(data["services"])
    except Exception as e:
        print(f"Erreur lors de la suppression du service actif: {e}")
        return 0

async def update_active_services_embed(bot):
    """Met à jour l'embed des services actifs"""
    try:
        data = load_active_services()
        services = data.get("services", [])
        
        embed = discord.Embed(
            title="📊 Services Actifs",
            description=f"**{len(services)}** employé(s) actuellement en service",
            color=0x1B1558
        )
        
        if not services:
            embed.add_field(
                name="Aucun service actif",
                value="Aucun employé n'est actuellement en service.",
                inline=False
            )
        else:
            for service in services:
                embed.add_field(
                    name=f"👤 {service['user_name']}",
                    value=(
                        f"**Type:** {service['service_type']}\n"
                        f"**Début:** {service['start_time']}\n"
                        f"**ID:** {service['user_id']}"
                    ),
                    inline=False
                )
        
        embed.set_footer(text="Los Santos Customs - Services Actifs")
        embed.set_image(url="https://i.goopics.net/ay1d82.png")
        
        # Trouver le canal
        channel = bot.get_channel(SERVICE_GESTION_CHANNEL_ID)
        if not channel:
            print(f"Canal de gestion de service introuvable: {SERVICE_GESTION_CHANNEL_ID}")
            return

        message_id = data.get("message_id")
        if message_id:
            try:
                message = await channel.fetch_message(message_id)
                await message.edit(embed=embed)
                return
            except discord.NotFound:
                pass
            except Exception as e:
                print(f"Erreur lors de la mise à jour du message: {e}")
        
        view = ForceFinServiceView(bot)

        # Créer un nouveau message
        try:
            new_message = await channel.send(embed=embed, view=view)
            data["message_id"] = new_message.id
            data["channel_id"] = channel.id
            save_active_services(data)
        except Exception as e:
            print(f"Erreur lors de la création du nouveau message: {e}")
            
    except Exception as e:
        print(f"Erreur dans update_active_services_embed: {e}")

async def update_services_embed(bot):
    """Met à jour l'embed des services actifs"""
    try:
        data = load_active_services()
        services = data.get("services", [])
    
        embed = discord.Embed(
            title="Gestion du service | 📊 Services Actifs",
            description=f"Cliquez sur un bouton pour prendre ou quitter votre service.\n**{len(services)}** employé(s) actuellement en service",
            color=0x1B1558
        )        
        if not services:
            embed.add_field(
                name="Aucun service actif",
                value="Aucun employé n'est actuellement en service.",
                inline=False
            )
        else:
            # Trier les services par nom d'utilisateur
            sorted_services = sorted(data["services"], key=lambda x: x["user_name"])
            
            # Ajouter chaque service avec une séparation
            for i, service in enumerate(sorted_services):
                embed.add_field(
                    name=f"👤 {service['user_name']}",
                    value=(
                        f"**Type:** {service['service_type']}\n"
                        f"**Début:** {service['start_time']}\n"
                        f"**ID:** {service['user_id']}"
                    ),
                    inline=False
                )
                
                # Ajouter une séparation sauf après le dernier
                if i != len(sorted_services) - 1:
                    embed.add_field(name="\u200b", value="━━━━━━━━━━━━━━━━━━━━", inline=False)
        
        embed.set_footer(text="Los Santos Customs - Services Actifs")
        embed.set_image(url="https://i.goopics.net/ay1d82.png")
        
        # Trouver le canal
        channel = bot.get_channel(SERVICE_CHANNEL_ID)
        if not channel:
            print(f"Canal de gestion de service introuvable: {SERVICE_CHANNEL_ID}")
            return

        message_service = data.get("message_service")
        if message_service:
            try:
                message = await channel.fetch_message(message_service)
                await message.edit(embed=embed)
                return
            except discord.NotFound:
                pass
            except Exception as e:
                print(f"Erreur lors de la mise à jour du message: {e}")
        
        view = ServiceButtonView(bot)

        # Créer un nouveau message
        try:
            new_message = await channel.send(embed=embed, view=view)
            data["message_service"] = new_message.id
            data["channel_service"] = channel.id
            save_active_services(data)
        except Exception as e:
            print(f"Erreur lors de la création du nouveau message: {e}")
            
    except Exception as e:
        print(f"Erreur dans update_services_embed: {e}")



def charger_employe():
    if not os.path.exists(FICHIER_EMPLOYES):
        with open(FICHIER_EMPLOYES, "w") as f:
            json.dump({"message_id": None, "channel_id": None, "employees": []}, f)
    with open(FICHIER_EMPLOYES, "r") as f:
        return json.load(f)

def sauvegarder_employe(data):
    with open(FICHIER_EMPLOYES, "w") as f:
        json.dump(data, f, indent=4)

async def update_employe(bot):
    data = charger_employe()
    channel = bot.get_channel(data["channel_id"])
    message = await channel.fetch_message(data["message_id"])

    embed = discord.Embed(
        title="📦 Liste des employés enregistrés",
        color=discord.Color.blue()
    )

    for i, employe in enumerate(sorted(data["employees"], key=lambda x: x["nom"])):
        embed.add_field(
            name=f"Employé {i + 1}",
            value=f"👤 {employe['nom']} {employe['prenom']}\n🔐 Numéro de téléphone : `{employe['telephone']}`\n📧 RIB : `{employe['rib']}`\n📧 Date de naissance : `{employe['date_naissance']}`",
            inline=False
        )
        # Ajoute une séparation sauf après le dernier
        if i != len(data["employees"]) - 1:
            embed.add_field(name="\u200b", value="━━━━━━━━━━━━━━━━━━━━", inline=False)
    
    await message.edit(embed=embed)

class AdvertButtonView(ui.View):
    def __init__(self, bot, user=None):
        super().__init__(timeout=None)
        self.bot = bot
        self.user = user
        self.add_item(self.AdvertButton(bot))

    class AdvertButton(ui.Button):
        def __init__(self, bot):
            super().__init__(label="Advert", style=discord.ButtonStyle.success, custom_id="advert_button")
            self.bot = bot
        async def callback(self, interaction: discord.Interaction):
            role = discord.utils.get(interaction.guild.roles, name="Service")
            if not role or role not in interaction.user.roles:
                await interaction.response.send_message("Vous devez être en service pour utiliser ce bouton.", ephemeral=True)
                return
            from datetime import datetime
            try:
                from zoneinfo import ZoneInfo
                now = datetime.now(ZoneInfo("Europe/Paris"))
            except Exception:
                now = datetime.now()
            now_str = now.strftime('%d/%m/%Y %H:%M')
            log_channel = self.bot.get_channel(ADVERT_CHANNEL_TARGET_ID)
            if log_channel:
                    log_embed = discord.Embed(
                        title="Log Advert",
                        description=f"Advert lancé par {interaction.user.mention} dans <#{ADVERT_CHANNEL_ID}> à {now_str}",
                        color=0x00ff00
                    )
                    await log_channel.send(embed=log_embed)
            await interaction.response.send_message("Advert effectué !", ephemeral=True)

class RCButtonView(ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot
        self.recrutement_ouvert = False  # État local des recrutements
        
        # Créer les boutons sur la même ligne
        self.on_button = ui.Button(label="🟢 Recrutement ON", style=discord.ButtonStyle.green, custom_id="rcon", row=0)
        self.off_button = ui.Button(label="🔴 Recrutement OFF", style=discord.ButtonStyle.red, custom_id="rcoff", row=0)
        
        # Ajouter les callbacks
        self.on_button.callback = self.rcon_callback
        self.off_button.callback = self.rcoff_callback
        
        # Ajouter les boutons à la vue
        self.add_item(self.on_button)
        self.add_item(self.off_button)
        
        # Mettre à jour l'état initial des boutons
        self.update_button_states()

    def update_button_states(self):
        """Met à jour l'état des boutons en fonction de l'état des recrutements"""
        self.on_button.disabled = self.recrutement_ouvert
        self.off_button.disabled = not self.recrutement_ouvert

    async def rcon_callback(self, interaction: discord.Interaction):
        """Callback pour le bouton Recrutement ON"""
        if not any(role.name == role_direction for role in interaction.user.roles):
            await interaction.response.send_message("❌ Vous n'avez pas les permissions nécessaires.", ephemeral=True)
            return
            
        self.recrutement_ouvert = True
        self.update_button_states()
        
        target_channel = self.bot.get_channel(RECRUTEMENT_CHANNEL_ID)
        if target_channel:
            embed = discord.Embed(
                title="Contact Los Santos Customs",
                description=f"Bonjour/Bonsoir,\n\n **Les recrutements sont actuellement ouverts : 🟢**. \n\n  Voici ce que vous devez envoyez à <@814277691981168680> pour postuler :\n - **Votre CV + Motivation** \n - **Vos Expériences**,\n - **Vos Horaires**.\n\n > ***Le temps de réponse est de 24 à 48h inclus.***\n\n  Merci à vous de l'intérêt que vous portez au Los Santos Customs.\n\n **Les recrutements ont été ouverts par {interaction.user.mention}**",
                color=0x00ff00
            )
            embed.set_image(url="https://i.goopics.net/ay1d82.png")
            await target_channel.send(embed=embed)
        
        await interaction.response.edit_message(view=self)
        await interaction.followup.send("✅ Recrutements ouverts avec succès!", ephemeral=True)

    async def rcoff_callback(self, interaction: discord.Interaction):
        """Callback pour le bouton Recrutement OFF"""
        if not any(role.name == role_direction for role in interaction.user.roles):
            await interaction.response.send_message("❌ Vous n'avez pas les permissions nécessaires.", ephemeral=True)
            return
            
        self.recrutement_ouvert = False
        self.update_button_states()
        
        target_channel = self.bot.get_channel(RECRUTEMENT_CHANNEL_ID)
        if target_channel:
            embed = discord.Embed(
                title="Contact Los Santos Customs",
                description=f"État des recrutements : 🔴\n\n **Les recrutements sont actuellement fermés : 🔴** \n\n Vous serez avertis lors de l'ouverture de ceux-ci. \n\n **Cordialement**,\n **La Direction**.\n\n *Recrutement OFF = 🔴* \n *Recrutement ON = 🟢* \n\n **Les recrutements ont été fermés par {interaction.user.mention}.**",
                color=0xff0000
            )
            embed.set_image(url="https://i.goopics.net/ay1d82.png")
            await target_channel.send(embed=embed)
        
        await interaction.response.edit_message(view=self)
        await interaction.followup.send("✅ Recrutements fermés avec succès!", ephemeral=True)

class ReasonSelect(ui.View):
    def __init__(self, bot, user):
        super().__init__(timeout=60)
        self.bot = bot
        self.user = user
        self.add_item(self.ReasonDropdown(bot, user))

    class ReasonDropdown(ui.Select):
        def __init__(self, bot, user):
            options = [
                discord.SelectOption(label="🟢 Recrutement ON", description="Recrutement ON"),
                discord.SelectOption(label="🔴 Recrutement OFF", description="Recrutement OFF"),
            ]
            super().__init__(placeholder="Sélectionnez une raison...", min_values=1, max_values=1, options=options, custom_id="reason_select")
            self.bot = bot
            self.user = user
            

        async def callback(self, interaction: discord.Interaction):
                reason = self.values[0]
                target_channel = self.bot.get_channel(RECRUTEMENT_CHANNEL_ID)
                if reason == "🟢 Recrutement ON":
                    embed = discord.Embed(
                        title="Contact Los Santos Customs",
                        description=f"Bonjour/Bonsoir,\n\n **Les recrutements sont actuellement ouverts : 🟢**. \n\n  Voici ce que vous devez envoyez à <@814277691981168680> pour postuler :\n - **Votre CV + Motivation** \n - **Vos Expériences**,\n - **Vos Horaires**.\n\n > ***Le temps de réponse est de 24 à 48h inclus.***\n\n  Merci à vous de l'intérêt que vous portez au Los Santos Customs.\n\n **Les recrutements ont été ouverts par {interaction.user.mention}**",
                        color=0x00ff00
                    )
                    embed.set_image(url="https://i.goopics.net/ay1d82.png")
                    
                    # Envoyer dans le canal ET répondre à l'interaction
                    await target_channel.send(embed=embed)
                    
                else:  # Recrutement OFF
                    embed = discord.Embed(
                        title="Contact Los Santos Customs",
                        description=f"État des recrutements : 🔴\n\n **Les recrutements sont actuellement fermés : 🔴** \n\n Vous serez avertis lors de l'ouverture de ceux-ci. \n\n **Cordialement**,\n **La Direction**.\n\n *Recrutement OFF = 🔴* \n *Recrutement ON = 🟢* \n\n **Les recrutements ont été fermés par {interaction.user.mention}.**",
                        color=0xff0000
                    )
                    embed.set_image(url="https://i.goopics.net/ay1d82.png")
                    
                    # Envoyer dans le canal ET répondre à l'interaction
                    await target_channel.send(embed=embed)

class ServiceButtonView(ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @ui.button(label="Prendre service", style=discord.ButtonStyle.success, custom_id="prendre_service")
    async def prendre_service(self, interaction: discord.Interaction, button: ui.Button):
        try:
            role = discord.utils.get(interaction.guild.roles, name="Service")
            if not role:
                await interaction.response.send_message("❌ Rôle 'Service' introuvable.", ephemeral=True)
                return
                
            if role in interaction.user.roles:
                await interaction.response.send_message("❌ Vous avez déjà pris votre service !", ephemeral=True)
                return
            
            # Ajouter le rôle
            await interaction.user.add_roles(role)
            
            # Obtenir l'heure actuelle
            from datetime import datetime
            try:
                from zoneinfo import ZoneInfo
                now = datetime.now(ZoneInfo("Europe/Paris"))
            except Exception:
                now = datetime.now()
            
            user_service_start[interaction.user.id] = now
            now_str = now.strftime('%d/%m/%Y %H:%M')
            
            # Ajouter dans les services actifs
            add_active_service(
                interaction.user.id,
                interaction.user.display_name,
                now_str,
                "Service normal"
            )
            
            # Créer l'embed de log
            embed = discord.Embed(
                title="Service 🟢",
                description=f"Prise de service de : {interaction.user.mention}\nDate : {now_str}",
                color=0x00ff00
            )
            
            # Envoyer le log
            target_channel = self.bot.get_channel(SERVICE_LOGS_CHANNEL_ID)
            if target_channel:
                await target_channel.send(embed=embed)
            
            await interaction.response.send_message("✅ Prise de service effectuée !", ephemeral=True)
            await update_active_services_embed(self.bot)
            await update_services_embed(self.bot)
            
        except Exception as e:
            print(f"Erreur dans prendre_service: {e}")
            await interaction.response.send_message("❌ Erreur lors de la prise de service.", ephemeral=True)

    @ui.button(label="Quitter service", style=discord.ButtonStyle.danger, custom_id="quitter_service")
    async def quitter_service(self, interaction: discord.Interaction, button: ui.Button):
        try:
            from datetime import datetime, timedelta
            try:
                from zoneinfo import ZoneInfo
                now = datetime.now(ZoneInfo("Europe/Paris"))
            except Exception:
                now = datetime.now()
            
            role = discord.utils.get(interaction.guild.roles, name="Service")
            if not role or role not in interaction.user.roles:
                await interaction.response.send_message("❌ Vous n'êtes pas en service.", ephemeral=True)
                return
            
            await interaction.user.remove_roles(role)
            remove_active_service(interaction.user.id)
            
            now_str = now.strftime('%d/%m/%Y %H:%M')
            embed = discord.Embed(
                title="Service 🔴",
                description=f"Fin de service de : {interaction.user.mention}\nDate : {now_str}",
                color=0xFF0000
            )
            
            target_channel = self.bot.get_channel(SERVICE_LOGS_CHANNEL_ID)
            if target_channel:
                await target_channel.send(embed=embed)
            
            await interaction.response.send_message("✅ Vous avez quitté votre service !", ephemeral=True)
            await update_active_services_embed(self.bot)
            await update_services_embed(self.bot)
            
        except Exception as e:
            print(f"Erreur dans quitter_service: {e}")
            await interaction.response.send_message("❌ Erreur lors de la fin de service.", ephemeral=True)

class ForceFinServiceView(ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @ui.button(label="🔴 Forcer fin de service", style=discord.ButtonStyle.danger, custom_id="force_fin_service", emoji="⚠️")
    async def force_fin_service(self, interaction: discord.Interaction, button: ui.Button):
        # Vérifier si l'utilisateur a le rôle de direction par nom
        role_name = "DIRECTION"  # Remplacez par le nom de votre rôle
        if not any(role.name == role_name for role in interaction.user.roles):
            await interaction.response.send_message("❌ Vous n'avez pas les permissions nécessaires pour utiliser cette fonction.", ephemeral=True)
            return
    

        data = load_active_services()
        services = data.get("services", [])
        
        if not services:
            await interaction.response.send_message("❌ Aucun employé en service actuellement.", ephemeral=True)
            return
        
        # Créer la vue avec le dropdown
        view = ForceFinServiceSelectView(self.bot, services)
        await interaction.response.send_message("Sélectionnez l'employé à forcer à quitter le service :", view=view, ephemeral=True)

class ForceFinServiceSelectView(ui.View):
    def __init__(self, bot, services):
        super().__init__(timeout=60)
        self.bot = bot
        self.add_item(self.ForceFinServiceDropdown(bot, services))

    class ForceFinServiceDropdown(ui.Select):
        def __init__(self, bot, services):
            self.bot = bot
            options = []
            for service in services:
                user_id = service.get("user_id")
                user_name = service.get("user_name", f"Utilisateur {user_id}")
                start_time = service.get("start_time", "Inconnu")
                
                # Essayer d'obtenir le nom d'utilisateur Discord si possible
                # (cette partie dépend de comment vous stockez les données)
                
                options.append(
                    discord.SelectOption(
                        label=user_name, 
                        description=f"Début: {start_time}", 
                        value=str(user_id),
                        emoji="🚗"
                    )
                )
            
                            
            max_values = min(25, len(options))  # Discord limite à 25 options max
            super().__init__(
                placeholder="Choisissez l'employé à forcer à quitter...", 
                min_values=1, 
                max_values=max_values,
                options=options, 
                custom_id="force_fin_service_select"
            )
            self.services = services

        async def callback(self, interaction: discord.Interaction):
                selected_user_id = int(self.values[0])
                
                # Vérifier si l'utilisateur est dans les services actifs
                data = load_active_services()
                user_service = None
                for service in data.get("services", []):
                    if service["user_id"] == str(selected_user_id):
                        user_service = service
                        break
                
                if not user_service:
                    await interaction.response.send_message("❌ Cet utilisateur n'est plus en service.", ephemeral=True)
                    return
                
                # Récupérer l'utilisateur
                guild = interaction.guild
                user = guild.get_member(selected_user_id)
                
                if not user:
                    await interaction.response.send_message("❌ Utilisateur introuvable sur ce serveur.", ephemeral=True)
                    return
                
                # Supprimer les rôles de service
                service_role = discord.utils.get(guild.roles, name="Service")
                
                roles_removed = []
                if service_role and service_role in user.roles:
                    await user.remove_roles(service_role)
                    roles_removed.append("Service")
                
                # Suppression des services actifs
                remove_active_service(selected_user_id)
                
                from datetime import datetime
                try:
                    from zoneinfo import ZoneInfo
                    now = datetime.now(ZoneInfo("Europe/Paris"))
                except Exception:
                    now = datetime.now()
                now_str = now.strftime('%d/%m/%Y %H:%M')
                
                # Envoyer l'embed de confirmation
                embed = discord.Embed(
                    title="⚠️ Service Forcé à l'arrêt",
                    description=(
                        f"**Employé:** {user.mention}\n"
                        f"**Par:** {interaction.user.mention}\n"
                        f"**Date:** {now_str}\n"
                        f"**Service type:** {user_service['service_type']}\n"
                        f"**Rôles retirés:** {', '.join(roles_removed) if roles_removed else 'Aucun'}"
                    ),
                    color=0xFF6A00
                )
                
                # Envoyer dans le canal de logs
                target_channel = self.bot.get_channel(SERVICE_LOGS_CHANNEL_ID)
                if target_channel:
                    await target_channel.send(embed=embed)
                
                # Mise à jour de l'embed des services actifs
                await update_active_services_embed(self.bot)
                await update_services_embed(self.bot)
                
                # Désactiver la vue après utilisation
                for item in self.view.children:
                    item.disabled = True
                
                await interaction.response.edit_message(
                    content=f"✅ Service forcé à l'arrêt pour **{user.display_name}**.", 
                    view=self.view
                )


async def refresh_absence_embed(bot):
    global absence_embed_message_id
    target_channel = bot.get_channel(ABSENCE_CHANNEL_ID)
    if not target_channel:
        print(f"[ERREUR] Salon absence introuvable: {ABSENCE_CHANNEL_ID}")
        return
    # Supprime l'ancien embed si présent
    if absence_embed_message_id:
        try:
            msg = await target_channel.fetch_message(absence_embed_message_id)
            await msg.delete()
        except Exception:
            pass
    embed = discord.Embed(
        title="Déclarer une absence",
        description="Cliquez sur le bouton ci-dessous pour déclarer une absence.",
        color=0x1B1558
    )
    view = AbsenceButtonView(bot)
    sent_msg = await target_channel.send(embed=embed, view=view)
    absence_embed_message_id = sent_msg.id

class AbsenceModal(ui.Modal, title="Déclarer une absence"):
    def __init__(self, bot, user):
        super().__init__()
        self.bot = bot
        self.user = user
        self.nom = ui.TextInput(label="Nom", placeholder="Votre nom", required=True)
        self.prenom = ui.TextInput(label="Prénom", placeholder="Votre prénom", required=True)
        self.date_debut = ui.TextInput(label="Date de début", placeholder="Ex: 10/06/2025", required=True)
        self.date_fin = ui.TextInput(label="Date de fin", placeholder="Ex: 15/06/2025", required=True)
        self.raison = ui.TextInput(label="Raison", placeholder="Motif de l'absence", required=True)
        self.add_item(self.nom)
        self.add_item(self.prenom)
        self.add_item(self.date_debut)
        self.add_item(self.date_fin)
        self.add_item(self.raison)

    async def on_submit(self, interaction: discord.Interaction):
        embed = discord.Embed(
            title="Nouvelle absence",
            description=f"Absence déclarée par {self.user.mention}",
            color=0x1B1558
        )
        embed.add_field(name="Nom", value=self.nom.value, inline=False)
        embed.add_field(name="Prénom", value=self.prenom.value, inline=False)
        embed.add_field(name="Date de début", value=self.date_debut.value, inline=True)
        embed.add_field(name="Date de fin", value=self.date_fin.value, inline=True)
        embed.add_field(name="Raison", value=self.raison.value, inline=False)
        absence_channel = interaction.guild.get_channel(ABSENCE_CHANNEL_ID)
        if absence_channel:
            await absence_channel.send(embed=embed)
            await interaction.response.send_message("Votre absence a bien été déclarée !", ephemeral=True)
            await refresh_absence_embed(self.bot)  # <-- AJOUT ICI
        else:
            await interaction.response.send_message("Salon d'absences introuvable.", ephemeral=True)

class InfoModal(discord.ui.Modal, title="Remplir ses informations"):
    def __init__(self, bot, user):
        super().__init__()
        self.bot = bot
        self.user = user
        self.nom = discord.ui.TextInput(label="Nom", placeholder="Ex: Doe", required=True)
        self.prenom = discord.ui.TextInput(label="Prénom", placeholder="Ex: John", required=True)
        self.date_naissance = discord.ui.TextInput(label="Date de naissance", placeholder="Ex: 01/01/2000", required=True)
        self.telephone = discord.ui.TextInput(label="Numéro de téléphone", placeholder="Ex: 555-1234", required=True)
        self.rib = discord.ui.TextInput(label="RIB", placeholder="Ex: 000000", required=True)
        self.add_item(self.nom)
        self.add_item(self.prenom)
        self.add_item(self.date_naissance)
        self.add_item(self.telephone)
        self.add_item(self.rib)

    async def on_submit(self, interaction: discord.Interaction):
        data = charger_employe()
        data["employees"] = [
            e for e in data["employees"]
            if not (e["nom"] == self.nom.value and e["prenom"] == self.prenom.value)
        ]
        data["employees"].append({
            "nom": self.nom.value,
            "prenom": self.prenom.value,
            "date_naissance": self.date_naissance.value,
            "telephone": self.telephone.value,
            "rib": self.rib.value
        })
        sauvegarder_employe(data)
        await interaction.response.send_message("Vos informations ont bien été envoyées !", ephemeral=True)
        await update_employe(interaction.client)

class InfoButtonView(ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @ui.button(label="Remplir ses informations", style=discord.ButtonStyle.success, custom_id="fill_info")
    async def fill_info(self, interaction: discord.Interaction, button: ui.Button):
        modal = InfoModal(self.bot, interaction.user)
        await interaction.response.send_modal(modal)

    @ui.button(label="Supprimer une fiche employé", style=discord.ButtonStyle.danger, custom_id="delete_employee")
    async def delete_employee(self, interaction: discord.Interaction, button: ui.Button):
        # Vérifie si l'utilisateur est admin
        if not interaction.user.guild_permissions.administrator:
            await interaction.response.send_message("Accès réservé aux administrateurs.", ephemeral=True)
            return

        # Modal pour demander le nom et prénom à supprimer
        class DeleteEmployeeModal(ui.Modal, title="Supprimer une fiche employé"):
            nom = ui.TextInput(label="Nom", placeholder="Ex: Doe", required=True)
            prenom = ui.TextInput(label="Prénom", placeholder="Ex: John", required=True)

            async def on_submit(self, interaction2: discord.Interaction):
                data = charger_employe()
                before = len(data["employees"])
                data["employees"] = [
                    e for e in data["employees"]
                    if not (e["nom"] == self.nom.value and e["prenom"] == self.prenom.value)
                ]
                sauvegarder_employe(data)
                after = len(data["employees"])
                if before == after:
                    await interaction2.response.send_message("Aucune fiche trouvée avec ce nom/prénom.", ephemeral=True)
                else:
                    await interaction2.response.send_message("Fiche employé supprimée avec succès.", ephemeral=True)
                    await update_employe(interaction2.client)

        await interaction.response.send_modal(DeleteEmployeeModal())

class AbsenceButtonView(ui.View):
    def __init__(self, bot):
        super().__init__(timeout=None)
        self.bot = bot

    @ui.button(label="Déclarer une absence", style=discord.ButtonStyle.primary, custom_id="absence")
    async def absence(self, interaction: discord.Interaction, button: ui.Button):
        modal = AbsenceModal(self.bot, interaction.user)
        await interaction.response.send_modal(modal)

class Event(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.Cog.listener()
    async def on_ready(self):
        print(f"✅ Bot connecté : {self.bot.user}")

    @commands.command(name="rc")
    @commands.has_role(role_direction)  # Seuls les membres avec le rôle "role_direction" peuvent exécuter cette commande
    async def rc(self, ctx):
        channel = RECRUTEMENT_CHANNEL_ID
        """Fait parler le bot dans le salon courant."""
        if channel:
            await channel.send(ReasonSelect(self.bot, ctx.author))
        elif not channel:
            print("Le salon de recrutement n'est pas défini.")
    
    @commands.command(name="dire")
    @commands.has_role(role_direction)  # Seuls les membres avec le rôle "role_direction" peuvent exécuter cette commande
    async def dire(self, ctx, *, message: str):
        """Fait parler le bot dans le salon courant."""
        await ctx.send(message)

    @commands.command(name="advert")
    @commands.has_role(role_direction)
    async def advert_embed(self, ctx):
        channel_advert = self.bot.get_channel(ADVERT_CHANNEL_ID)
        """Envoie un embed avec le bouton vert Advert."""
        embed = discord.Embed(title="Faire un Advert", description="Cliquez sur le bouton pour envoyer un advert.", color=0x1B1558)
        view = AdvertButtonView(self.bot, user=ctx.author)
        await channel_advert.send(embed=embed, view=view)

    @commands.command(name='actif_service')
    @commands.has_role(role_direction)  # Seuls les membres avec le rôle "role_direction" peuvent exécuter cette commande
    async def actif_service(self, ctx):
        """Affiche les services actifs avec le bouton de fin forcée."""
        data = load_active_services()
        services = data.get("services", [])
        
        embed = discord.Embed(
            title="📊 Services Actifs",
            description=f"**{len(services)}** employé(s) actuellement en service",
            color=0x1B1558
        )
        
        for service in services:
            embed.add_field(
                name=f"👤 {service['user_name']}",
                value=(
                    f"**Type:** {service['service_type']}\n"
                    f"**Début:** {service['start_time']}\n"
                    f"**ID:** {service['user_id']}"
                ),
                inline=False
            )
        
        embed.set_footer(text="Los Santos Customs - Services Actifs")
        embed.set_image(url="https://i.goopics.net/ay1d82.png")
        
        # Envoyer avec la view qui contient le bouton
        message = await ctx.send(embed=embed, view=ForceFinServiceView(self.bot))   
        
        # Sauvegarder l'ID du message pour les futures mises à jour
        data["channel_id"] = ctx.channel.id
        data["message_id"] = message.id     
        save_active_services(data)

    @commands.command(name="infos")
    async def infos(self, ctx):
        data = charger_employe()
        embed = discord.Embed(
            title="Informations personnelles",
            description="Aucun employé enregistré pour le moment.",
            color=discord.Color.blue()
        )

        sent_msg = await ctx.send(embed=embed, view = InfoButtonView(self.bot))

        data["channel_id"] = ctx.channel.id
        data["message_id"] = sent_msg.id
        sauvegarder_employe(data)
        await update_employe(self.bot)
        print("[DEBUG] Embed infos envoyé tout en bas.")

    @commands.command(name="absence")
    @commands.has_role(role_direction)
    async def absence_embed(self, ctx):
        """Envoie un embed avec le bouton pour déclarer une absence."""
        embed = discord.Embed(
            title="Déclarer une absence",
            description="Cliquez sur le bouton ci-dessous pour déclarer une absence.",
            color=0x1B1558
        )
        view = AbsenceButtonView(self.bot)
        await ctx.send(embed=embed, view=view)

    @commands.command(name="embed")
    @commands.has_role(role_direction)  # Seuls les membres avec le rôle "role_direction" peuvent exécuter cette commande
    async def embedimage(self, ctx, titre: str, image_url: str, *, texte: str = None):
        """Créer un embed avec un titre, une image et un texte optionnel (commande texte, style drafbot)."""
        embed = discord.Embed(title=titre, color=0x1B1558)
        if texte:
            embed.description = texte
        embed.set_image(url=image_url)
        await ctx.send(embed=embed)

    @commands.command(name="service")
    @commands.has_role(role_direction)  # Seuls les membres avec le rôle "role_direction" peuvent exécuter cette commande
    async def service(self, ctx):
        channel_service = self.bot.get_channel(SERVICE_CHANNEL_ID)
        """Envoie un embed avec les boutons Prendre service / Quitter service pour gérer un rôle précis."""
        data = load_active_services()
        services = data.get("services", [])
        embed = discord.Embed(
            title="Gestion du service | 📊 Services Actifs :",
            description=f"Cliquez sur un bouton pour prendre ou quitter votre service.\n" \
                        f"**{len(services)}** employé(s) actuellement en service",
            color=0x1B1558
        )
        embed.set_image(url="https://i.goopics.net/ay1d82.png")
        for service in services:
            embed.add_field(
                name=f"👤 {service['user_name']}",
                value=(
                    f"**Type:** {service['service_type']}\n"
                    f"**Début:** {service['start_time']}\n"
                    f"**ID:** {service['user_id']}"
                ),
                inline=False
            )
        
        message = await channel_service.send(embed=embed, view=ServiceButtonView(self.bot))
        # Sauvegarder l'ID du message pour les futures mises à jour
        data["channel_id"] = ctx.channel.id
        data["message_service"] = message.id     
        save_active_services(data)    



    @commands.command(name="rc")
    @commands.has_role(role_direction)
    async def rc(self, ctx):
        """Affiche les boutons de gestion des recrutements"""
        channel = self.bot.get_channel(RECRUTEMENT_CHANNEL_ID)
        if channel:
            embed = discord.Embed(
                title="**Los Santos Customs** Recrutements", 
                description="Cliquez sur le bouton pour changer l'état des recrutements.", 
                color=0x1B1558
            )
            embed.set_footer(text="Los Santos Customs - Recrutements")
            view = RCButtonView(self.bot)
            await ctx.send(embed=embed, view=view)
            await ctx.send("✅ Embed de recrutement envoyé!", ephemeral=True)
        else:
            await ctx.send("❌ Salon de recrutement introuvable.", ephemeral=True)


async def setup(bot):
    await bot.add_cog(Event(bot))
    bot.add_view(ServiceButtonView(bot))
    bot.add_view(RCButtonView(bot))