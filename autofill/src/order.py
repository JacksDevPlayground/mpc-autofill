import os
import sys
from concurrent.futures import ThreadPoolExecutor
from glob import glob
from queue import Queue
from typing import DefaultDict, Optional
from xml.etree.ElementTree import Element, ParseError

import attr
import enlighten
import InquirerPy
import src.constants as constants
from defusedxml.ElementTree import parse as defused_parse
from sanitize_filename import sanitize
from src.utils import (
    CURRDIR,
    TEXT_BOLD,
    TEXT_END,
    ValidationException,
    download_google_drive_file,
    file_exists,
    get_google_drive_file_name,
    image_directory,
    text_to_list,
    unpack_element,
)


@attr.s
class CardImage:
    drive_id: str = attr.ib(default="")
    slots: list[int] = attr.ib(default=[])
    name: Optional[str] = attr.ib(default="")
    file_path: Optional[str] = attr.ib(default="")
    query: Optional[str] = attr.ib(default=None)

    downloaded: bool = attr.ib(init=False, default=False)
    uploaded: bool = attr.ib(init=False, default=False)
    errored: bool = attr.ib(init=False, default=False)

    # region file system interactions

    def file_exists(self) -> bool:
        """
        Determines whether this image has been downloaded successfully.
        """

        return file_exists(self.file_path)

    def retrieve_card_name(self) -> None:
        """
        Retrieves the file's name based on Google Drive ID. `None` indicates that the file on GDrive is invalid.
        """

        if not self.name:
            self.name = get_google_drive_file_name(drive_id=self.drive_id)

    def generate_file_path(self) -> None:
        """
        Sets `self.file_path` according to the following logic:
        * If `self.drive_id` points to a valid file in the user's file system, use it as the file path
        * If a file with `self.name` exists in the `cards` directory, use the path to that file as the file path
        * Otherwise, use `self.name` with `self.drive_id` in parentheses in the `cards` directory as the file path.
        """

        if file_exists(self.drive_id):
            self.file_path = self.drive_id
            self.name = os.path.basename(self.file_path)
            return

        if not self.name:
            self.retrieve_card_name()

        if self.name is None:
            self.file_path = None
        else:
            file_path = os.path.join(image_directory(), sanitize(self.name))
            if not os.path.isfile(file_path) or os.path.getsize(file_path) <= 0:
                # The filepath without ID in parentheses doesn't exist - change the filepath to contain the ID instead
                name_split = self.name.rsplit(".", 1)
                file_path = os.path.join(
                    image_directory(), sanitize(f"{name_split[0]} ({self.drive_id}).{name_split[1]}")
                )
            self.file_path = file_path

    # endregion

    # region initialisation

    def validate(self) -> None:
        self.errored = any([self.errored, self.name is None, self.file_path is None])

    def __attrs_post_init__(self) -> None:
        self.generate_file_path()
        self.validate()

    # endregion

    # region public

    @classmethod
    def from_element(cls, element: Element, slot_offset: Optional[int] = 0) -> "CardImage":
        card_dict = unpack_element(element, [x.value for x in constants.DetailsTags])
        drive_id = ""
        if (drive_id_text := card_dict[constants.CardTags.id].text) is not None:
            drive_id = drive_id_text.strip(' "')
        slots = []
        if (slots_text := card_dict[constants.CardTags.slots].text) is not None:
            # This can be a list of slots or a single slot
            slots = text_to_list(slots_text,slot_offset)
            name = None
        if constants.CardTags.name in card_dict.keys():
            name = card_dict[constants.CardTags.name].text
        query = None
        if constants.CardTags.name in card_dict.keys():
            query = card_dict[constants.CardTags.query].text
        card_image = cls(drive_id=drive_id, slots=slots, name=name, query=query)
        return card_image

    def download_image(self, queue: Queue["CardImage"], download_bar: enlighten.Counter) -> None:
        if not self.file_exists() and not self.errored and self.file_path is not None:
            self.errored = not download_google_drive_file(self.drive_id, self.file_path)

        if self.file_exists() and not self.errored:
            self.downloaded = True
        else:
            print(
                f"Failed to download '{TEXT_BOLD}{self.name}{TEXT_END}' - "
                f"allocated to slot/s {TEXT_BOLD}[{', '.join([str(x) for x in self.slots])}]{TEXT_END}.\n"
                f"Download link - {TEXT_BOLD}https://drive.google.com/uc?id={self.drive_id}&export=download{TEXT_END}\n"
            )
        # put card onto queue irrespective of whether it was downloaded successfully or not
        queue.put(self)
        download_bar.update()

    # endregion


@attr.s
class CardImageCollection:
    """
    A collection of CardImages for one face of a CardOrder.
    """

    cards: list[CardImage] = attr.ib(default=[])
    queue: Queue[CardImage] = attr.ib(init=False, default=attr.Factory(Queue))
    num_slots: int = attr.ib(default=0)
    slot_offset: int = attr.ib(default=0)
    face: constants.Faces = attr.ib(default=constants.Faces.front)

    # region initialisation

    def all_slots(self, slot_offset: Optional[int] = 0) -> set[int]:
        return set(range(slot_offset, self.num_slots + slot_offset))

    def slots(self) -> set[int]:
        return {y for x in self.cards for y in x.slots}
    
    def card_count(self) -> int:
        return len(self.cards)

    def validate(self) -> None:
        if self.num_slots == 0 or not self.cards:
            raise ValidationException(f"{self.face} has no images!")
        slots_missing = self.all_slots() - self.slots()
        if slots_missing:
            print(
                f"Warning - the following slots are empty in your order for the {self.face} face: "
                f"{TEXT_BOLD}{sorted(slots_missing)}{TEXT_END}"
            )

    # endregion

    # region public

    @classmethod
    def from_element(
        cls, element: Element, num_slots: int, face: constants.Faces, fill_image_id: Optional[str] = None, slot_offset: Optional[int] = 0
    ) -> "CardImageCollection":
        card_images = []
        if element:
            for x in element:
                card_images.append(CardImage.from_element(x,slot_offset))
        card_image_collection = cls(cards=card_images, num_slots=num_slots, face=face)
        if fill_image_id:
            # Bug: I don't think this is working with the offset :( 
            
            # fill the remaining slots in this card image collection with a new card image based off the given id
            missing_slots = card_image_collection.all_slots(slot_offset) - card_image_collection.slots()
            if missing_slots:
                card_image_collection.cards.append(
                    CardImage(
                        drive_id=fill_image_id.strip(' "'),
                        slots=list(missing_slots),
                    )
                )

        # postponing validation from post-init so we don't error for missing slots that `fill_image_id` would fill
        try:
            card_image_collection.validate()
        except ValidationException as e:
            input(f"There was a problem with your order file:\n\n{TEXT_BOLD}{e}{TEXT_END}\n\nPress Enter to exit.")
            sys.exit(0)
        return card_image_collection

    def download_images(self, pool: ThreadPoolExecutor, download_bar: enlighten.Counter) -> None:
        """
        Set up the provided ThreadPoolExecutor to download this collection's images, updating the given progress
        bar with each image. Async function.
        """

        pool.map(lambda x: x.download_image(self.queue, download_bar), self.cards)

    # endregion


@attr.s
class Details:
    total: int = attr.ib(default=0)
    bracket: int = attr.ib(default=0)
    stock: str = attr.ib(default=constants.Cardstocks.S30.value)
    foil: bool = attr.ib(default=False)
    decks: int = attr.ib(default=1)

    # region initialisation

    def validate(self) -> None:
        if not 0 < self.total <= self.bracket:
            raise ValidationException(
                f"Order total {self.total} outside allowable range of {TEXT_BOLD}[0, {self.bracket}]{TEXT_END}!"
            )
        if self.bracket not in constants.BRACKETS:
            raise ValidationException(f"Order bracket {self.bracket} not supported!")
        if self.stock not in [x.value for x in constants.Cardstocks]:
            raise ValidationException(f"Order cardstock {self.stock} not supported!")

    def __attrs_post_init__(self) -> None:
        try:
            self.validate()
        except ValidationException as e:
            input(f"There was a problem with your order file:\n\n{TEXT_BOLD}{e}{TEXT_END}\n\nPress Enter to exit.")
            sys.exit(0)

    # endregion
    

    # region public

    @classmethod
    def from_element(cls, element: Element) -> "Details":
        details_dict = unpack_element(element, [x.value for x in constants.DetailsTags])
        total = 0
        if (total_text := details_dict[constants.DetailsTags.total].text) is not None:
            total = int(total_text)
        bracket = 0
        if (bracket_text := details_dict[constants.DetailsTags.bracket].text) is not None:
            bracket = int(bracket_text)
        stock = details_dict[constants.DetailsTags.stock].text or constants.Cardstocks.S30
        foil: bool = details_dict[constants.DetailsTags.foil].text == "true"
        decks: int = int(details_dict[constants.DetailsTags.decks].text)

        details = cls(total=total, bracket=bracket, stock=stock, foil=foil, decks=decks)
        return details

    # endregion  

@attr.s
class CardOrder:
    name: Optional[str] = attr.ib(default=None)
    details: Details = attr.ib(default=None)
    decks: list[CardImageCollection] = attr.ib(default=[])
    
    # TODO: add support for multiple card orders
    fronts: list[CardImageCollection] = attr.ib(default=[])
    backs: list[CardImageCollection] = attr.ib(default=[])

    # region logging

    def print_order_overview(self) -> None:
        if self.name is not None:
            print(f"Successfully parsed card order: {TEXT_BOLD}{self.name}{TEXT_END}")
        print(
            f"Your order has a total of {TEXT_BOLD}{self.details.total}{TEXT_END} cards, in the MPC bracket of up "
            f"to {TEXT_BOLD}{self.details.bracket}{TEXT_END} cards.\n{TEXT_BOLD}{self.details.stock}{TEXT_END} "
            f"cardstock ({TEXT_BOLD}{'foil' if self.details.foil else 'nonfoil'}{TEXT_END}).\n "
        )

    # endregion

    # region initialisation

    def validate(self) -> None:
        for deck in self.decks:
            for collection in [self.deck.fronts, self.deck.backs]:
                for image in collection.cards:
                    if not image.file_path:
                        raise ValidationException(
                            f"Image {TEXT_BOLD}{image.name}{TEXT_END} in {TEXT_BOLD}{collection.face}{TEXT_END} "
                            f"has no file path."
                        )

    def __attrs_post_init__(self) -> None:
        try:
            self.validate()
        except ValidationException as e:
            input(f"There was a problem with your order file:\n\n{TEXT_BOLD}{e}{TEXT_END}\n\nPress Enter to exit.")
            sys.exit(0)

    @classmethod
    def from_element(cls, element: Element, name: Optional[str] = None) -> "CardOrder":
        root_dict = unpack_element(element, [x.value for x in constants.BaseTags])
        details = Details.from_element(root_dict[constants.BaseTags.details])
        
        # TODO: add support for multiple card orders       
        # fronts = combine all details.decks.fronts into one collection
    
        combinedFronts = []
        combinedBacks = []
        lastQuantity = 0
        print("Found %d decks" %details.decks)
        
        for deck in range(details.decks):
            currentDeck = root_dict[constants.BaseTags.decks][deck]
            unpack = unpack_element(currentDeck, [x.value for x in constants.DeckTags])  
            quantity: int = int(unpack[constants.DeckTags.quantity].text) # 4
            offset:int = lastQuantity
                      
            combinedFronts.append(CardImageCollection.from_element(
                element=unpack[constants.DeckTags.fronts],
                num_slots=quantity,
                slot_offset=offset,
                face=constants.Faces.front
            ))
        
            # backs = combine all details.decks.backs into one collection
            if details.decks > 1:
                cardback_elem = unpack[constants.DeckTags.cardback]
                if cardback_elem.text is not None:
                    combinedBacks.append(CardImageCollection.from_element(
                        element=unpack[constants.DeckTags.backs],
                        num_slots=quantity,
                        slot_offset=offset,
                        face=constants.Faces.back,
                        fill_image_id=cardback_elem.text,
                    ))
                else:
                    print(f"{TEXT_BOLD}Warning{TEXT_END}: Your order file did not contain a common cardback image.")
                    combinedBacks.append(CardImageCollection.from_element(
                        element=unpack[constants.DeckTags.backs],
                        num_slots=quantity,
                        slot_offset=offset,
                        face=constants.Faces.back,
                    ))
            else:
                unpack = unpack_element(root_dict[constants.BaseTags.decks][0], [x.value for x in constants.DeckTags])  
                cardback_elem = unpack[constants.DeckTags.cardback]
                if cardback_elem.text is not None:
                    backs = CardImageCollection.from_element(
                        element=root_dict[constants.BaseTags.backs],
                        num_slots=details.total,
                        face=constants.Faces.back,
                        fill_image_id=cardback_elem.text,
                    )
                else:
                    print(f"{TEXT_BOLD}Warning{TEXT_END}: Your order file did not contain a common cardback image.")
                    backs = CardImageCollection.from_element(
                        element=root_dict[constants.BaseTags.backs],
                        num_slots=details.total,
                        face=constants.Faces.back,
                    )                      
            lastQuantity = lastQuantity + quantity
            
        fronts = combinedFronts
        backs = combinedBacks        
        order = cls(name=name, details=details, fronts=fronts, backs=backs)
        return order

    @classmethod
    def from_file_name(cls, file_name: str) -> "CardOrder":
        try:
            xml = defused_parse(file_name)
        except ParseError:
            input("Your XML file contains a syntax error so it can't be processed. Press Enter to exit.")
            sys.exit(0)
        print(f"Parsing XML file {TEXT_BOLD}{file_name}{TEXT_END}...")
        order = cls.from_element(xml.getroot(), name=file_name)
        return order

    # endregion

    # region public

    @classmethod
    def from_xml_in_folder(cls) -> "CardOrder":
        """
        Reads an XML from the current directory, offering a choice if multiple are detected, and populates this
        object with the contents of the file.
        """

        xml_glob = list(glob(os.path.join(CURRDIR, "*.xml")))
        if len(xml_glob) <= 0:
            input("No XML files found in this directory. Press enter to exit.")
            sys.exit(0)
        elif len(xml_glob) == 1:
            file_name = xml_glob[0]
        else:
            xml_select_string = "Multiple XML files found. Please select one for this order: "
            questions = {
                "type": "list",
                "name": "xml_choice",
                "message": xml_select_string,
                "choices": xml_glob,
            }
            answers = InquirerPy.prompt(questions)
            file_name = answers["xml_choice"]
        return cls.from_file_name(file_name)

    # endregion
