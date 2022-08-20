![build](https://github.com/chilli-axe/mpc-autofill/actions/workflows/build.yml/badge.svg)
![tests_black_isort_mypy](https://github.com/chilli-axe/mpc-autofill/actions/workflows/tests_black_isort_mypy.yml/badge.svg)
[![Github all releases](https://img.shields.io/github/downloads/chilli-axe/mpc-autofill/total.svg)](https://GitHub.com/chilli-axe/mpc-autofill/releases/)

# mpc-autofill


- ✨✨✨ Adds multiple decks to a single order (Very manual process - but it works 🤣)

![](/img/works.png)

### To make it work:

>  **Note**
> This adds a few extra fields/tags to the cards.xml (You need to add these manually)

- Here is the new layout for the `cards.xml` file. 
- You will need to change `details.quantity` -> `details.total`. (Total of all decks - In the example below 4+4)
- You will need to add `details.decks` tag
- You will need to add a `decks` tag
- You will need to move `fronts`, `backs`, `cardback` into a new `decks.deck` tag
- You will need to add a `deck.quantity` tag with the total number for that deck (In the example below there are 4 cards)
  
```xml
<order>
    <details>
        <total>8</total>
        <bracket>18</bracket>
        <stock>(S30) Standard Smooth</stock>
        <foil>false</foil>
        <decks>2</decks>
    </details>
    <decks>
        <deck>
            <quantity>4</quantity>
            <fronts>
                <card>
                    <id>18ZwnupYqJmqiiVURddaj2vTaZbK87rY2</id>
                    <slots>0</slots>
                    <name>Bala Ged Recovery (Lucas Staniec).jpg</name>
                    <query>Bala Ged Recovery</query>
                </card>
                <card>
                    <id>1XfNuT1Fv6LJN0sP-FXS6a3t-5tmcZhXV</id>
                    <slots>1</slots>
                    <name>Bootleggers' Stash.png</name>
                    <query>bootleggers stash</query>
                </card>
                <card>
                    <id>1huXW2YcNuiNAbQhFyiTYDXApTxoap6F1</id>
                    <slots>2</slots>
                    <name>Chatterfang, Squirrel General.jpg</name>
                    <query>chatterfang squirrel general</query>
                </card>
                <card>
                    <id>1srQTz1W35pFCgtxXnDc239rhXhAXWTVX</id>
                    <slots>3</slots>
                    <name>Harvest Season.png</name>
                    <query>harvest season</query>
                </card>
            </fronts>
            <backs>
                <card>
                    <id>16isHStHKn4LfHPWNS3VGyURVffBdNXrE</id>
                    <slots>0</slots>
                    <name>Bala Ged Sanctuary (Extended Lucas Staniec).jpg</name>
                    <query>bala ged sanctuary</query>
                </card>
            </backs>
            <cardback>1LrVX0pUcye9n_0RtaDNVl2xPrQgn7CYf</cardback>
        </deck>
        <deck>
            <quantity>4</quantity>
            <fronts>
                <card>
                    <id>1cBYrjNoJJ47NWdGUuzmZXco19k5to2YZ</id>
                    <slots>0</slots>
                    <name>Captains Claws.jpg</name>
                    <query>captains claws</query>
                </card>
                <card>
                    <id>1AF4q7L5OBs2pDbY0mePXgFaQLKoa4A8n</id>
                    <slots>1</slots>
                    <name>Isshin, Two Heavens as One.png</name>
                    <query>isshin two heavens as one</query>
                </card>
                <card>
                    <id>1AWWbmgIHwMuRfeWEaqN5MsgqALE37cYs</id>
                    <slots>2</slots>
                    <name>Malakir Rebirth (Marta Nael).jpg</name>
                    <query>Malakir Rebirth</query>
                </card>
                <card>
                    <id>1EnOtB_AkGQZ4bvew6LOichPOce5ZjYG8</id>
                    <slots>3</slots>
                    <name>Valakut Awakening (Extended Campbell White).jpg</name>
                    <query>Valakut Awakening</query>
                </card>
            </fronts>
            <backs>
                <card>
                    <id>1FvJBhYDDsHMZxSsPovgMjBbWsafqtjxt</id>
                    <slots>2</slots>
                    <name>Malakir Mire (Marta Nael).jpg</name>
                    <query>malakir mire</query>
                </card>
                <card>
                    <id>15KnYJfteDULEyFo7B6CDwa_f_48DwcP9</id>
                    <slots>3</slots>
                    <name>Valakut Stoneforge (Extended Campbell White).jpg</name>
                    <query>valakut stoneforge</query>
                </card>
            </backs>
            <cardback>1d0jCveC1CP3hNAx34D42E_RCxfz5W_3R</cardback>
        </deck>
    </decks>
</order>
```

Automating MakePlayingCards's online ordering system.

If you're here to download the desktop client, check the [Releases](https://github.com/chilli-axe/mpc-autofill/releases) tab.

# Monorepo Structure
* Web project:
  * Located in `/MPCAutofill`,
  * Backend is Django 4 with Elasticsearch (sqlite is fine), frontend is Jquery,
  * Indexes images stored in the Google Drives connected to the project,
  * Facilitates the generation of XML orders for use with the desktop client,
  * Intended to be deployed as a web application but can also be spun up locally with Docker.
* Desktop client:
  * Located in `/autofill`,
  * Responsible for parsing XML orders, downloading images from Google Drive, and automating MPC's order creation interface.

Each component of the project has its own README; check those out for more details.

# Requirements
* Python 3.9+ and the packages specified in `requirements.txt` for each component (web project and desktop client).

# Contributing
* Please ensure that you install the `pre-commit` Python package and run `pre-commit install` before committing any code to your branch / PR - this will run `black` and `isort` on your code to maintain consistent styling, and run `mypy` to catch any static typing issues.
