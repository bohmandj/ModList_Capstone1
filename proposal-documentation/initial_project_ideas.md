<div style="text-align: right">David Bohman</div>  
<div style="text-align: right">Software Engineering Career Track</div>  
<div style="text-align: right">Capstone 1: Project Idea Brainstorm</div>

# Project Ideas  

## Idea 1: D&D Reference and/or Character Sheet Builder (basically a simplified roll20.net)  

**Problem:** D&D the table top game has a TON of rules and details that players and dungeon masters need in order to play the game. It is common to have to look things up during gameplay, and the player's handbook is 255 pages of content, so using an easily searchable website is preferred by many. Character sheets can also be complicated and are frequently updated, so tools to save and update that data can be beneficial.  

https://open5e.com/api-docs  
https://5e-bits.github.io/docs/api  
Both of the APIs above provide Dungeons & Dragons 5th Edition content to retrieve monsters, spells, items, rules, or just about anything else a player or DM would need.  

* Ideas for unauthenticated users:
    * Provide on-screen links to detail-page information grouped by content category, as well as keyword search if you know what you’re looking for specifically.  
* Ideas for logged in users (some might be stretch goals):  
    * Bookmarking for information a user may need to reference more frequently. Could be grouped by campaign or character for easier access.  
    * Adding posts to a community forum with commenting and up/down voting.  
    * A character sheet building tool for making a new character from scratch. Could be used to store multiple different characters, and update characters as you level up. Maybe include random name generator and/or text text based image generation for character images depending what APIs I can find and how ambitious I'm feeling.  


## Idea 2a: To-Be-Read Book App (basically goodreads.com)  
 
**Problem:** As exemplified by the Goodreads app and website, many readers like to search for information about books, keep track of and review the books they have read, have a reliable place to go for recommendations, and a way to keep track of books they want to read in the future.  

https://openlibrary.org/developers/api - contains detailed information about books that could be used to populate the book details for this capstone.  
https://developer.overdrive.com/apis - contains a suite of APIs that allow third-party applications to connect to and interact with the OverDrive digital media database (library related things).

* Ideas for unauthenticated users:  
    * Search for books, authors, or genres, and get information like title, author, page count, and reviews/recommendations for books. 
* Ideas for logged in users (some might be stretch goals):
    * Users can place books on their already-read or want-to-read “bookshelves”.  
    * Already read books can get ratings, comments, and user-generated suggestions for “if you liked this, you’ll also like…”.   
    * User “bookshelves” with ratings and comments will be publicly visible, and users can follow other users to see new books being read by like minded readers.  
    * There could be a feature to estimate how long it should take a user to read a selected book based on user-provided average page or word reading speed. Maybe provide a tool to give them that estimate?
    * Need to do more research, but if possible, connect to libby for audio books or the library for physical books for browsing and checking out (or placing holds) without having to leave the site.


## Idea 2b: To-Be-Played Video Game App (basically goodreads.com but for video games)  
_My current frontrunner idea_  

**Problem:** Much like in Idea 2a, many gamers like to search for information about games, keep track of and review the games they have read, have a reliable place to go for reviews/recommendations, and a way to keep track of games they want to play in the future.

https://rawg.io/apidocs - RAWG is a game database and discovery service, providing comprehensive video game data for 500,000+ games, search, and machine learning recommendations.  
https://apidocs.cheapshark.com/ - CheapShark is a price comparison website for digital PC Games that keeps track of prices across multiple stores including Steam, GreenManGaming, Fanatical, and many others.  
https://www.freetogame.com/api-doc - provides access to a comprehensive database of free-to-play games and free MMO games  
  
* Ideas for unauthenticated users:  
    * Search for video games, game studios, or game genres, and be provided information like title, game studio, rating, price comparison.  
* Ideas for logged in users (some might be stretch goals):
    * Already played games can get ratings, comments, and user-generated suggestions for “if you liked this, you’ll also like…”.  
    * Users can place games on their already-played or want-to-play game lists.  
    * User made game lists with ratings and comments will be publicly visible, and users can follow other users to see new games being played by like minded gamers.
    * Stretch goal? Aggregate game price information from multiple sources to find the best deals and provide links to seller’s sites to purchase.  


## Idea 3: Multi-store Product Price Comparison

**Problem:** Shoppers want to know they're getting the best price and usually don't really care who they get the product from, so we should provide a resource to aggregate current prices for the same products across multiple major retailers and web stores.  

Many big stores have their own APIs, or there are web scrapers that can provide real-time pricing information.

* Search for products across multiple stores to compare prices and get links to selected store’s product page to purchase from them.  
* Aggregated reviews for products to get a wider view of what people think instead of only the people who shopped at a specific store.  
* Users can add their own reviews as well as bookmark products or add similar products to a product comparison page to improve their shopping experience.  
