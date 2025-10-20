#!/usr/bin/env python3
"""
Pydantic models for Audible API responses (aligned to the official API JSON).
"""

from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field


class Author(BaseModel):
    asin: Optional[str] = None
    name: str


class Narrator(BaseModel):
    name: str


class Series(BaseModel):
    asin: Optional[str] = None
    sequence: Optional[str] = None
    title: Optional[str] = None
    url: Optional[str] = None


class CategoryLadder(BaseModel):
    id: str
    name: str


class CategoryLadderGroup(BaseModel):
    ladder: List[CategoryLadder]
    root: str


class RatingDistribution(BaseModel):
    average_rating: Optional[float] = None
    display_average_rating: Optional[str] = None
    display_stars: Optional[float] = None
    num_five_star_ratings: Optional[int] = None
    num_four_star_ratings: Optional[int] = None
    num_one_star_ratings: Optional[int] = None
    num_ratings: Optional[int] = None
    num_three_star_ratings: Optional[int] = None
    num_two_star_ratings: Optional[int] = None


class Rating(BaseModel):
    num_reviews: Optional[int] = None
    overall_distribution: Optional[RatingDistribution] = None
    performance_distribution: Optional[RatingDistribution] = None
    story_distribution: Optional[RatingDistribution] = None


class ProductImages(BaseModel):
    image_500: Optional[str] = Field(default=None, alias="500")
    image_700: Optional[str] = Field(default=None, alias="700")
    image_1000: Optional[str] = Field(default=None, alias="1000")

    class Config:
        populate_by_name = True


class AvailableCodec(BaseModel):
    enhanced_codec: Optional[str] = None
    format: Optional[str] = None
    is_kindle_enhanced: Optional[bool] = None
    name: Optional[str] = None


class SocialMediaImages(BaseModel):
    facebook: Optional[str] = None
    ig_bg: Optional[str] = None
    ig_static_with_bg: Optional[str] = None
    ig_sticker: Optional[str] = None
    twitter: Optional[str] = None


class AudibleProduct(BaseModel):
    asin: str
    title: str
    authors: List[Author] = []
    narrators: List[Narrator] = []
    series: List[Series] = []
    category_ladders: List[CategoryLadderGroup] = []
    rating: Optional[Rating] = None
    product_images: Optional[ProductImages] = None
    language: Optional[str] = None
    publisher_name: Optional[str] = None
    publication_datetime: Optional[str] = None
    release_date: Optional[str] = None
    runtime_length_min: Optional[int] = None
    extended_product_description: Optional[str] = None
    publisher_summary: Optional[str] = None
    copyright: Optional[str] = None
    format_type: Optional[str] = None
    is_adult_product: Optional[bool] = None
    content_delivery_type: Optional[str] = None
    content_type: Optional[str] = None
    has_children: Optional[bool] = None
    is_listenable: Optional[bool] = None
    is_pdf_url_available: Optional[bool] = None
    is_purchasability_suppressed: Optional[bool] = None
    is_vvab: Optional[bool] = None
    issue_date: Optional[str] = None
    date_first_available: Optional[str] = None
    merchandising_description: Optional[str] = None
    merchandising_summary: Optional[str] = None
    platinum_keywords: List[str] = []
    product_site_launch_date: Optional[str] = None
    publication_name: Optional[str] = None
    read_along_support: Optional[str] = None
    sku: Optional[str] = None
    sku_lite: Optional[str] = None
    social_media_images: Optional[SocialMediaImages] = None
    thesaurus_subject_keywords: List[str] = []
    voice_description: Optional[str] = None
    asset_details: List[Any] = []
    available_codecs: List[AvailableCodec] = []


class AudibleAPIResponse(BaseModel):
    product: AudibleProduct
    response_groups: List[str]
