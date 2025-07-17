"""
Service layer for video research application.
Contains business logic separated from route handlers.
"""
from typing import List, Dict, Tuple, Optional, Any
from models import (
    Participant, Video, VideoCategory, VideoInteraction, 
    WatchingTime, Preference, CopingStrategy, ConsistencyAnswer, MessageTime
)
from config import db
from flask import current_app
import random


class VideoInteractionService:
    """Service for handling video interactions (like, dislike, star, comment)."""
    
    @staticmethod
    def handle_like_dislike(participant_number: str, video_id: int, action: str) -> None:
        """Handle like/dislike interactions, removing previous conflicting actions."""
        # Remove existing like/dislike for this video
        VideoInteraction.query.filter_by(
            participant_number=participant_number,
            video_id=video_id
        ).filter(VideoInteraction.action.in_(['like', 'dislike'])).delete(synchronize_session=False)
        
        # Add new interaction
        new_interaction = VideoInteraction(
            participant_number=participant_number,
            video_id=video_id,
            action=action,
            content=''
        )
        db.session.add(new_interaction)

    @staticmethod
    def handle_remove_action(participant_number: str, video_id: int, action: str) -> None:
        """Handle removal of like/dislike actions."""
        target_action = action.split('_')[1]  # 'remove_like' -> 'like'
        VideoInteraction.query.filter_by(
            participant_number=participant_number,
            video_id=video_id,
            action=target_action
        ).delete(synchronize_session=False)

    @staticmethod
    def handle_star_action(participant_number: str, video_id: int, action: str) -> None:
        """Handle star/unstar interactions."""
        if action == 'star':
            # Check if already starred to avoid duplicates
            existing = VideoInteraction.query.filter_by(
                participant_number=participant_number,
                video_id=video_id,
                action='star'
            ).first()
            if not existing:
                db.session.add(VideoInteraction(
                    participant_number=participant_number,
                    video_id=video_id,
                    action='star',
                    content=''
                ))
        else:  # star_remove
            VideoInteraction.query.filter_by(
                participant_number=participant_number,
                video_id=video_id,
                action='star'
            ).delete(synchronize_session=False)

    @staticmethod
    def handle_comment(participant_number: str, video_id: int, comment_text: str) -> bool:
        """Handle comment interactions. Returns True if successful."""
        if not comment_text or not comment_text.strip():
            return False
        
        db.session.add(VideoInteraction(
            participant_number=participant_number,
            video_id=video_id,
            action='comment',
            content=comment_text.strip()
        ))
        return True


class VideoSelectionService:
    """Service for video selection and categorization logic."""
    
    @staticmethod
    def get_unwatched_videos_for_categories(
        participant_number: str, 
        category_ids: List[int], 
        exclude_round: int = 1
    ) -> Dict[int, List[Video]]:
        """Get unwatched videos grouped by category for a participant."""
        watched_video_ids = db.session.query(WatchingTime.video_id).filter(
            WatchingTime.participant_number == participant_number,
            WatchingTime.round_number == exclude_round,
            Video.category_id.in_(category_ids)
        ).join(Video, Video.id == WatchingTime.video_id).all()
        
        watched_ids = [row[0] for row in watched_video_ids]
        
        available_videos = Video.query.filter(
            Video.category_id.in_(category_ids),
            ~Video.id.in_(watched_ids) if watched_ids else True
        ).all()
        
        # Group by category
        videos_by_category = {}
        for video in available_videos:
            if video.category_id not in videos_by_category:
                videos_by_category[video.category_id] = []
            videos_by_category[video.category_id].append(video)
        
        return videos_by_category

    @staticmethod
    def select_videos_for_preferences(
        participant_number: str, 
        preferences: List[Preference]
    ) -> Tuple[List[Dict], List[str]]:
        """Select one video per preferred category for continued viewing."""
        if len(preferences) != 3:
            raise ValueError("Exactly 3 preferences required")

        category_ids = [pref.category_id for pref in preferences]
        videos_by_category = VideoSelectionService.get_unwatched_videos_for_categories(
            participant_number, category_ids
        )
        
        chosen_videos = []
        selected_categories = []
        
        for pref in preferences:
            category_videos = videos_by_category.get(pref.category_id, [])
            
            # Fallback: get any video from this category if no unwatched ones
            if not category_videos:
                category_videos = Video.query.filter_by(category_id=pref.category_id).all()
            
            if category_videos:
                video = random.choice(category_videos)
                chosen_videos.append({
                    'id': video.id,
                    'title': video.title,
                    'link': video.url,
                })
                selected_categories.append(pref.category.name)
        
        return chosen_videos, selected_categories


class ParticipantService:
    """Service for participant-related operations."""
    
    @staticmethod
    def get_participant_preferences(participant_number: str, round_number: int) -> List[Preference]:
        """Get participant's category preferences for a specific round."""
        return Preference.query.filter_by(
            participant_number=participant_number, 
            round_number=round_number
        ).all()

    @staticmethod
    def get_remaining_categories(participant_number: str, round_number: int = 1) -> List[VideoCategory]:
        """Get categories not selected in a previous round."""
        selected_categories = ParticipantService.get_participant_preferences(participant_number, round_number)
        selected_category_ids = [pref.category_id for pref in selected_categories]
        
        return VideoCategory.query.filter(
            VideoCategory.name != 'info',
            ~VideoCategory.id.in_(selected_category_ids) if selected_category_ids else True
        ).all()


class AdditionalInfoService:
    """Service for handling additional information form processing."""
    
    @staticmethod
    def process_time_spent(participant_number: str, time_spent_str: str) -> Optional[MessageTime]:
        """Process and validate time spent data."""
        try:
            time_spent = float(time_spent_str)
            if time_spent > 0:
                current_app.logger.info(f"Time spent recorded: {time_spent}s for participant {participant_number}")
                return MessageTime(
                    participant_number=participant_number,
                    time_spent=time_spent
                )
        except ValueError:
            current_app.logger.warning(f"Invalid timeSpent value: {time_spent_str} for participant {participant_number}")
        return None

    @staticmethod
    def process_consistency_answers(
        participant_number: str, 
        q1_str: Optional[str], 
        q2_str: Optional[str]
    ) -> List[ConsistencyAnswer]:
        """Process and validate consistency answer data."""
        records = []
        if q1_str is not None and q2_str is not None:
            try:
                q1, q2 = int(q1_str), int(q2_str)
                records.extend([
                    ConsistencyAnswer(
                        participant_number=participant_number,
                        question_number=1,
                        answer=q1
                    ),
                    ConsistencyAnswer(
                        participant_number=participant_number,
                        question_number=2,
                        answer=q2
                    )
                ])
                current_app.logger.info(f"Consistency answers recorded: q1={q1}, q2={q2} for participant {participant_number}")
            except ValueError:
                current_app.logger.warning(f"Invalid consistency answers: q1={q1_str}, q2={q2_str} for participant {participant_number}")
        return records

    @staticmethod
    def process_strategy_choice(participant_number: str, strategy: str) -> Optional[CopingStrategy]:
        """Process and validate strategy choice."""
        if strategy:
            current_app.logger.info(f"Strategy recorded: {strategy} for participant {participant_number}")
            return CopingStrategy(
                participant_number=participant_number,
                strategy=strategy
            )
        return None

    @staticmethod
    def determine_redirect_route(strategy: Optional[str]) -> str:
        """Determine the appropriate redirect route based on strategy."""
        if not strategy:
            return 'coping_strategy'
        
        strategy_routes = {
            'watch_other': 'select_categories_round2',
            'learn_more': 'info_cocoons'
        }
        return strategy_routes.get(strategy, 'continue_same_categories')


class StrategyRedirectService:
    """Service for handling strategy-based redirects."""
    
    STRATEGY_ROUTES = {
        'watch_other': 'select_categories_round2',
        'learn_more': 'info_cocoons',
        'avoidance': 'continue_same_categories'
    }
    
    @staticmethod
    def get_redirect_route(strategy: str) -> str:
        """Get the appropriate route for a given strategy."""
        return StrategyRedirectService.STRATEGY_ROUTES.get(
            strategy, 
            'continue_same_categories'  # Default fallback
        )
