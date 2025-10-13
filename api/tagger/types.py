#!/usr/bin/env python3
"""
Type definitions for Audible API responses
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass

@dataclass
class Author:
    asin: str
    name: str

@dataclass
class Narrator:
    name: str

@dataclass
class Series:
    asin: str
    sequence: str
    title: str
    url: str

@dataclass
class CategoryLadder:
    id: str
    name: str

@dataclass
class CategoryLadderGroup:
    ladder: List[CategoryLadder]
    root: str

@dataclass
class RatingDistribution:
    average_rating: float
    display_average_rating: str
    display_stars: float
    num_five_star_ratings: int
    num_four_star_ratings: int
    num_one_star_ratings: int
    num_ratings: int
    num_three_star_ratings: int
    num_two_star_ratings: int

@dataclass
class Rating:
    num_reviews: int
    overall_distribution: RatingDistribution
    performance_distribution: Optional[RatingDistribution] = None
    story_distribution: Optional[RatingDistribution] = None

@dataclass
class ProductImages:
    image_500: str
    image_700: str
    image_1000: str

@dataclass
class AudibleProduct:
    asin: str
    title: str
    authors: List[Author]
    narrators: List[Narrator]
    series: List[Series]
    category_ladders: List[CategoryLadderGroup]
    rating: Rating
    product_images: ProductImages
    language: str
    publisher_name: str
    publication_datetime: str
    release_date: str
    runtime_length_min: int
    extended_product_description: str
    publisher_summary: str
    copyright: str
    format_type: str
    is_adult_product: bool
    content_delivery_type: str
    content_type: str
    has_children: bool
    is_listenable: bool
    is_pdf_url_available: bool
    is_purchasability_suppressed: bool
    is_vvab: bool
    issue_date: str
    date_first_available: str
    merchandising_description: str
    merchandising_summary: str
    platinum_keywords: List[str]
    product_site_launch_date: str
    publication_name: str
    read_along_support: str
    sku: str
    sku_lite: str
    social_media_images: Dict[str, str]
    thesaurus_subject_keywords: List[str]
    voice_description: str
    asset_details: List[Any]
    available_codecs: List[Any]

@dataclass
class AudibleAPIResponse:
    product: AudibleProduct
    response_groups: List[str]
