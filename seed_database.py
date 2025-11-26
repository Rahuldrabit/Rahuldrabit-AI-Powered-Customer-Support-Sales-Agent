"""Seed database with test data."""

from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import random

from app.models.database import (
    SessionLocal, User, Conversation, Message,
    Platform, ConversationStatus, MessageSender, MessageIntent
)


def seed_database():
    """Seed the database with test data."""
    db = SessionLocal()
    
    try:
        print("🌱 Seeding database with test data...")
        
        # Create test users
        users = []
        for i in range(5):
            user = User(
                platform=random.choice([Platform.TIKTOK, Platform.LINKEDIN]),
                platform_user_id=f"user_{i+1}_{random.randint(1000, 9999)}",
                username=f"testuser{i+1}",
                display_name=f"Test User {i+1}"
            )
            db.add(user)
            users.append(user)
        
        db.commit()
        print(f"✅ Created {len(users)} test users")
        
        # Create test conversations
        conversations = []
        test_messages = [
            ("Hey, I ordered a blue hoodie 3 days ago but haven't received tracking info", MessageIntent.SUPPORT, False),
            ("What's the pricing for your enterprise plan for 50 users?", MessageIntent.SALES, False),
            ("This is ridiculous! I've been charged twice and no one is helping!", MessageIntent.URGENT, True),
            ("Hello, I have a question about your product", MessageIntent.GENERAL, False),
            ("My order #AB123456 still hasn't arrived after 2 weeks", MessageIntent.SUPPORT, False),
        ]
        
        for user in users:
            platform_conv_id = f"conv_{user.platform_user_id}_{random.randint(1000, 9999)}"
            conv = Conversation(
                user_id=user.id,
                platform=user.platform,
                platform_conversation_id=platform_conv_id,
                status=ConversationStatus.ACTIVE,
                created_at=datetime.utcnow() - timedelta(days=random.randint(0, 7))
            )
            db.add(conv)
            conversations.append(conv)
        
        db.commit()
        print(f"✅ Created {len(conversations)} test conversations")
        
        # Create test messages
        message_count = 0
        for i, conv in enumerate(conversations):
            # User message
            user_msg_text, intent, is_urgent = test_messages[i % len(test_messages)]
            
            user_msg = Message(
                conversation_id=conv.id,
                sender_type=MessageSender.USER,
                content=user_msg_text,
                intent=intent,
                sentiment_score=random.uniform(-1.0, 1.0),
                created_at=datetime.utcnow() - timedelta(minutes=random.randint(5, 120))
            )
            db.add(user_msg)
            message_count += 1
            
            # Agent response
            if intent == MessageIntent.SUPPORT:
                response = "Thank you for reaching out! I understand your concern. Could you please provide your order number so I can look into this for you right away?"
            elif intent == MessageIntent.SALES:
                response = "Thank you for your interest in our enterprise plan! For 50 users, our pricing starts at $2,499 per month. I'd be happy to schedule a demo to show you all the features. Would that work for you?"
            elif intent == MessageIntent.URGENT:
                response = "I understand this is important to you, and I want to make sure you get the best possible assistance. I'm connecting you with a human agent who will be able to help you right away."
                conv.escalated = True
                conv.escalation_reason = "Urgent issue detected - customer frustration"
                conv.status = ConversationStatus.ESCALATED
            else:
                response = "Hello! Thanks for getting in touch. How can I assist you today?"
            
            agent_msg = Message(
                conversation_id=conv.id,
                sender_type=MessageSender.AGENT,
                content=response,
                intent=intent,
                sentiment_score=0.5,
                response_time_ms=random.randint(200, 1500),
                created_at=datetime.utcnow() - timedelta(minutes=random.randint(0, 115))
            )
            db.add(agent_msg)
            message_count += 1
        
        db.commit()
        print(f"✅ Created {message_count} test messages")
        
        # Summary
        print("\n📊 Database seeded successfully!")
        print(f"   - Users: {len(users)}")
        print(f"   - Conversations: {len(conversations)}")
        print(f"   - Messages: {message_count}")
        print(f"   - Escalated: {sum(1 for c in conversations if c.escalated)}")
        
    except Exception as e:
        print(f"❌ Error seeding database: {e}")
        db.rollback()
    finally:
        db.close()


if __name__ == "__main__":
    seed_database()
