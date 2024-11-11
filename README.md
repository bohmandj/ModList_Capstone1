# Capstone One: ModList

## ModList Project Overview

**Website:**

[https://modlist.onrender.com/](https://modlist.onrender.com/)

**Problem:**

 The popular video game mod hosting website Nexus Mods ([nexusmods.com](https://nexusmods.com)) lacks a good way to bookmark, save, or otherwise organize non-downloaded mods as you browse the 600,000+ mods (across 3000+ games) hosted on their site, looking for new mods to add to your games.

**Solution Concept:**

Create the ModList website to provide mod bookmarking and organization functionality currently unavailable to the video game modding community using Nexus Mods. 

To use ModList, the user must first have an account on Nexus Mods. Nexus has very good mod browsing and search functionality, which is not available to third party sites through their API. It is recommended that finding new mods should be done on the official Nexus site. 

The Tracking feature on Nexus can allow users to keep tabs on mods they want to bookmark with a single click, and will automatically import to their 'Nexus Tracking' mod list on the ModList site when they log in with their ModList username and password, and provide their Nexus Personal API Key. 

Once logged in to ModList and connected to Nexus, users can add or move mods from the base import modlist that every profile starts with, 'Nexus Tracked Mods', to any number of custom modlists they make. Modlists can be used to plan new builds, group similar mods into custom categories, or however else a user wants to organize them.

**Future Development:**

In future updates, users will also be able to follow other users to see what new lists they're building or which mods they're adding to their lists. Individual lists will also be able to be followed for easy reference. A timeline will be added so you can keep up with what the users and lists you follow have been doing. Additionally, at some point I would like to build indicators into the mod cards inside of lists to alert users when another mod is required for, or conflicts with, a mod in your list.

<br>

## API

**Nexus Mods Public API**

The [Nexus Mods Public API](https://app.swaggerhub.com/apis-docs/NexusMods/nexus-mods_public_api_params_in_form_data/1.0#/) allows third-party applications to access the Nexus Mods database, provided they are supplying a valid API Key for a user. Users can view their own API Keys by visiting their [API Keys](https://www.nexusmods.com/users/myaccount?tab=api%20access) page on Nexus. (This is the current implementation on ModList - a user must provide their Nexus Personal API Key on login for the site to function.)

Applications can also implement integrations without the user having to manage their own keys by using the Nexus Mods [Single Sign-On (SSO)](https://github.com/Nexus-Mods/sso-integration-demo). Head to the link for documentation and a simple demo of the SSO. (This will likely be implemented on Modlist in a future version.)

Nexus utilizes user-based rate limiting on their API, with rate limits of: 2,500 requests within 24 hours and once this limit has been exceeded by a user they are then restricted to 100 requests per hour.

<br>

## Tech Stack

**ModList is a Python application using a Flask web framework to perform CRUD operations on an SQL database.**

+ **Languages -**
Python, JavaScript, HTML, CSS

+ **Web Frameworks -**
Flask

+ **Database -**
PostgreSQL, Supabase

+ **ORM (Object Relational Mapping) -**
SQLAlchemy, Flask-SQLAlchemy

+ **Templating Engine -**
Jinja2

+ **Forms & Validation -**
WTForms, bcrypt

+ **API Architecture -**
RESTful APIs

+ **Hosting & Deployment -**
Render

+ **Testing -**
Python Unittest

<br>

## Modlist Site Functionality / Features

**Database Interaction:**

+ **Sign Up & Authentication -**
Accounts can only be accessed by authenticated users. Username and hashed password (using bcrypt) provided at login must match records stored in the database.

+ **User Info Editing -**
Form (using WTForms) can be submitted to change user data in the database. Username, Email, Password, and NSFW mod content visibility can be edited.

+ **User Deletion -**
User accounts can be deleted from the database, also deleting any modlists or association table relations linked to the user.

+ **Modlist Creation -**
Users can create new modlists with custom name, and optional description and private designation to hide modlist from showing on public profile.

+ **Modlist Editing -**
Users can edit the name, description, and private designation of their modlists. 

+ **Modlist Deletion -**
Users can delete their modlists from the database, also deleting any association table relations to the user, mods, or games.

+ **Adding Mods to Modlists -**
Mods can be added and removed from modlists. The first mod added to a modlist assigns the modlist to a specific game and limits new additions to mods for that game.

+ **Removing Mods from Modlists -**
Mods can be added and removed from modlists. The final mod removed from a modlist removes the game assignment from the modlist and mods for any game can be added.

+ **Syncing Tracked Mods -**
Nexus Tracked Mods modlist adds or removes mods to match list of tracked mods returned from API call. Sync happens on login or user hits sync button.

+ **Change Keep-Tracked Status -**
Users can add or remove Keep-Tracked status from mods in Nexus Tracked Mods modlist to accommodate intended purpose of tracking on Nexus.

**API Interaction:**

+ **GET Game Data -**
GET request to retrieve list of all games.

+ **GET Mod Data -**
GET request to retrieve all data for single mod, trending mods, latest added mods, or latest updated mods.

+ **GET Tracked Mods -**
GET request to retrieve list of all mods in user's Tracking Center on Nexus.

+ **POST Mod Endorsement -**
POST request to change user's endorsement status of a specific mod on Nexus.

+ **POST/DELETE Mod Tracking -**
POST and DELETE requests to add or remove a mod from user's Tracking Centre on Nexus.

<br>

## Problem Background Info

**What is Nexus?**

 This capstone project is intended to be a website for gamers who modify their video games, also known as "modders". To get their mods, many from the modding community use the popular video game mod hosting website **Nexus Mods**, [nexusmods.com](https://nexusmods.com/), to browse and download. It is a fantastic resource, hosting over 600,000+ mods across 3000+ games, and has some built in tools that work great for what they're intended to do. There is a new '**Collections**' feature that can group and publish your mod collection from Vortex Mod Manager to Nexus as a pre-made build list for other users to download with all the same versions and settings from the curator's build. Nexus also has a '**Tracking**' feature that is intended to notify users when mods they've downloaded and are using get new updates.  
 
**What needed improving?**

 Nexus obviously has a TON of mods. So what do you do if you're browsing the "popular mods" page on Nexus and find 30 new mods that look interesting but don't fit the current build you're working on? For many computers, drive space is too precious to download them all before you know when or even if you'll want to use them. Plus, right now you're just browsing to see what is out there! You might realize, once you dig a little deeper, that many of these mods might conflict with each other and won't work right if downloaded and deployed together. 
 
 But these mods seem awesome and you still don't want to lose them! How are you supposed to keep track of these non-downloaded mods?

 **Nexus Collections** are great, but it's a tool for, and intended to be used in, Vortex Mod Manager. In Vortex the curator can make a collection from one of their profile's build lists that they have already installed, deployed, load order corrected, and tested to make sure it works before publishing it to Nexus. The Collection's curator can also build from scratch and refine as they go before publishing, but either case, Vortex only has access to mods you've already installed so you need to download mods before they can be added to a collection. 
 
 **Nexus Tracking** could be a good way to keep track of mods, but since it is not the intended purpose of the tracking feature, the filtering and organization on the tracking page has sub-par sorting capabilities and no way to group mods or organize them to make finding the one you're looking for easy.

<br>

## Standard Modlist Site User Flow

**Note: Registration & API Key**

In order to use ModList, a Nexus Personal API Key is needed in order to interact with Nexus and have your Tracking Centre and Nexus Tracked Mods modlist sync. If a new user doesn't have a Nexus account, they will need to [sign up for a Nexus account](https://users.nexusmods.com/register) and get their API Key from the bottom of [this page](https://www.nexusmods.com/users/myaccount?tab=api%20access) in order to log in after signing up for a ModList account.

**Note: General Navigation**

For signed in users, the top right corner of the page has a navigation dropdown that will take users to the games page, their user profile, their Nexus Tracked Mods modlist, or to the form that creates a new modlist.

**Homepage:**

Once signed in, the homepage is the signed in user's profile page that shows all of their modlists, organized by game and displayed by most recently updated. From here, they can edit their profile details, create new empty modlists, or navigate to the Nexus Tracked Mods list or any other of their custom modlists. Because this site is meant to be supplementary to a modder's use of Nexus, there are orange buttons that will open the related page on Nexus in a new browser tab. These links to the official site can be found on most pages, so the full functionality of Nexus stays easily accessible.

**Nexus Tracked Mods List:**

Due to the limitations of Nexus' public API, the Nexus Tracked Mods modlist was built to be the core of ModList's functionality. The Nexus API doesn't provide an efficient way to retrieve lots of mods for searching or browsing, plus Nexus' main site is already great for finding interesting new mods. What the API *does* provide is the ability to request a list of all of the mods a user has tracked in the Nexus Tracking Centre of the Nexus account linked to the API key they used to log in to ModList. Tracking and un-tracking mods on Nexus is super easy while browsing, so this list of tracked mods is the best way to import mods from Nexus' site over to ModList.

When signing in, the mods in the Nexus Tracked Mods modlist automatically sync to the list of mods in the Tracking Centre on Nexus. From this modlist, the 'Add Mod to ModList' button on any mod card allows users to easily add the mod to a custom modlist they own. If a user is actively using both sites, and tracking or un-tracking mods on Nexus, there is a 'Re-Sync Tracked Mods to Nexus' button to update your tracked mods on ModList on demand.

However, importing mods to ModList is not the intended purpose of 'tracking' on Nexus. The Tracking Centre on Nexus is intended to be a list of mods a user has installed and wants update notifications for within Nexus. Because of this, mods in the Nexus Tracked Mods modlist are split into two tabs - 'Imported Tracked Mods', and 'Keep-Tracked Mods'. The Imported tab is where new mods the user tracked on Nexus will import into. If a user only tracked a mod to import it to ModList, a 'Un-track on Nexus' button on the mod card makes it easy to remove from the Tracking Centre once it's been added it to a custom modlist. The Keep-Tracked tab is where mods a user wants to keep in the Tracking Centre for notifications can be moved to using the 'Add to Keep-Tracked' button. Mods on the Keep-Tracked tab also do not have a 'Un-track on Nexus' button, so they won't accidentally get un-tracked when removing mods from the Tracking Centre on Nexus from the Import tab. 

**Making a Modlist:**

From the homepage/user's profile page, the user's Nexus Tracked Mods modlist, or even the form to add a mod to a modlist, the form to create a new modlist can be accessed. Making a new modlist only requires a name that is unique from any other modlists the user has made. Optionally, a description of the modlist can be added, or the modlist can be marked as private so it doesn't appear on the user's public profile page.

**Viewing Mods:**

While viewing the official mod page on Nexus is the best way to see all details, a mod page on ModList does include the mod's summary, some stats, as well as additional ways to interact with the mod. From any modlist, clicking on the title of a mod will direct the user to that mod's page. On a mod's page, you can add the mod to a modlist, add it to or remove it from the Nexus Tracking Centre, endorse or un-endorse the mod using the Nexus account linked to the API key, or open the mod on Nexus in a new tab for all information about the mod.

**Viewing Games:**

From mod pages and some mod cards, the name of the game the mod was made for is a link that will take you to the game's page on ModList. Browsing capabilities through the Nexus Public API is limited, but the game page on ModList is able to show a handful of mods for that game, grouped by Trending, Latest Added, and Latest Updated. Each category also has a link to open the corresponding page on Nexus in a new tab to see more.

There is also a page for all games, that has an expandable list of all games ordered by popularity, as well as a menu to search games alphabetically by title. This page can be accessed from any individual game page or the main navigation dropdown in the top right corner of all pages.

<br>



