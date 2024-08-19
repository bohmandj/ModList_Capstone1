# Capstone One: ModList

## API

**Nexus Mods Public API**

The Nexus Mods Public API allows third-party applications to access the Nexus Mods database, provided they are supplying a valid API Key for a user. Users can view their own API Keys by visiting their [API Keys](https://www.nexusmods.com/users/myaccount?tab=api%20access) page on Nexus.

Applications can also implement integrations without the user having to manage their own keys by using the Nexus Mods [Single Sign-On (SSO)](https://github.com/Nexus-Mods/sso-integration-demo). Head to the link for documentation and a simple demo of the SSO.

Nexus utilizes user-based rate limiting on their API, with rate limits of: 2,500 requests within 24 hours and once this limit has been exceeded by a user they are then restricted to 100 requests per hour.

## ModList Project Overview

**Problem:**

 The popular video game mod hosting website Nexus Mods ([nexusmods.com](https://nexusmods.com)) lacks a good way to bookmark, save, or otherwise organize non-downloaded mods as you browse the 600,000+ mods (across 3000+ games) hosted on their site looking for interesting new things to add to your game.

**Solution Concept:**

Create the ModList website to provide mod bookmarking and organization functionality currently unavailable to the video game modding community using Nexus Mods. 

To use ModList, the user must first have an account on Nexus Mods. Nexus has very good mod browsing and search functionality, which is not available to third party sites through their API, so all finding of new mods will be done there. The Tracking feature on Nexus can allow users to keep tabs on mods they want to bookmark with a single click, and will automatically import to their 'Nexus Tracking' mod list on the ModList site when they log in and connect to Nexus through the Single Sign On feature. 

Once logged in to ModList and connected to Nexus, users can add or move mods from the base import list, 'Nexus Tracking', to any number of custom lists they make. Lists can be used to plan new builds, group similar mods into custom categories, or just however else they want to organize them. Users can also follow other users to see what new lists they're building or which mods they're adding to their lists. Individual lists can also be followed for easy reference.

## Problem Background Info: 

**What is Nexus?**

 This capstone project is intended to be a website for gamers who modify their video games, also known as "modders". To get their mods, many from the modding community use the popular video game mod hosting website **Nexus Mods**, [nexusmods.com](https://nexusmods.com/), to browse and download. It is a fantastic resource, hosting over 600,000+ mods across 3000+ games, and has some built in tools that work great for what they're intended to do. There is a new '**Collections**' feature that can group and publish your mod collection from Vortex Mod Manager to Nexus as a pre-made build list for other users to download with all the same versions and settings from the curator's build. Nexus also has a '**Tracking**' feature that is intended to notify users when mods they've downloaded and are using get new updates.  
 
**What did I think needed fixing?**

 Nexus obviously has a TON of mods. So what do you do if you're browsing Nexus' "popular mods" page and find 30 new mods that look interesting but don't fit the current build you're working on? For many computers, drive space is too precious to download them all before you know when or even if you'll want to use them. Plus, right now you're just browsing to see what is out there! You might realize, once you dig a little deeper, that many of these mods might conflict with each other and won't work right if downloaded and deployed together. 
 
 But these mods seem awesome and you still don't want to lose them! How are you supposed to keep track of these non-downloaded mods?

 Nexus Collections are great, but it's a tool for, and intended to be used in, Vortex Mod Manager. In Vortex the curator can copy one of their profiles' installed, deployed, load order corrected, and tested build lists. The Collection's curator can also build from scratch, but either case, Vortex only has access to mods you've already installed so you need to download mods before they can be added. 
 
 Nexus Tracking could be a good way to keep track of mods, but since it is not the intended purpose of the tracking feature, the filtering and organization on the tracking page has sub-par sorting capabilities and no way to group mods or organize them to make finding the one you want easy.
