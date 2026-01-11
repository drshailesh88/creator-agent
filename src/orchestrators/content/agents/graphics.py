"""Graphics Agent - Handles visual content generation prompts."""

from typing import Any, Dict, List, Optional
import logging
from datetime import datetime

from ...base.agent import BaseAgent, AgentTool, ResponseFormat


logger = logging.getLogger(__name__)


class GraphicsAgent(BaseAgent):
    """
    Graphics Agent for visual content creation.

    Capabilities:
    - Infographic generation prompts
    - Chart and diagram descriptions
    - Image prompt generation for DALL-E, Midjourney, etc.
    - Visual design recommendations
    """

    SYSTEM_PROMPT = """You are an expert visual content designer specializing in creating prompts and specifications for visual assets.

Your capabilities include:
1. Creating detailed prompts for AI image generators (DALL-E, Midjourney, Stable Diffusion)
2. Designing infographic layouts and content specifications
3. Describing charts and data visualizations
4. Creating diagram specifications (flowcharts, mind maps, etc.)

Design principles:
- Clarity: Visual elements should communicate information clearly
- Hierarchy: Important information should be visually prominent
- Consistency: Maintain visual consistency across assets
- Accessibility: Consider color contrast and readability
- Brand alignment: Match visual style to brand guidelines

For each visual type, consider:
- Purpose and key message
- Target audience
- Platform/size requirements
- Color scheme and style
- Text elements and placement"""

    # Supported visual types
    VISUAL_TYPES = [
        "infographic", "chart", "diagram", "illustration",
        "banner", "thumbnail", "social_image", "presentation"
    ]

    # Supported image generators
    IMAGE_GENERATORS = ["dalle", "midjourney", "stable_diffusion", "ideogram"]

    def __init__(
        self,
        model: str = "glm-4",
        model_config: Optional[Dict[str, Any]] = None
    ):
        super().__init__(
            model=model,
            model_config=model_config,
            response_format=ResponseFormat.JSON
        )
        self._last_tools_used: List[str] = []

    def _initialize_tools(self) -> None:
        """Initialize graphics tools."""

        # Infographic Generator
        self.register_tool(AgentTool(
            name="generate_infographic",
            description="Generate specifications for an infographic",
            func=self._generate_infographic,
            parameters={
                "topic": {
                    "type": "string",
                    "description": "Topic for the infographic"
                },
                "data_points": {
                    "type": "array",
                    "description": "Key data points to include"
                },
                "style": {
                    "type": "string",
                    "description": "Visual style: modern, minimal, corporate, playful",
                    "default": "modern"
                },
                "dimensions": {
                    "type": "object",
                    "description": "Width and height specifications"
                }
            },
            required_params=["topic"]
        ))

        # Chart Description Generator
        self.register_tool(AgentTool(
            name="describe_chart",
            description="Generate chart/visualization description",
            func=self._describe_chart,
            parameters={
                "chart_type": {
                    "type": "string",
                    "description": "Type: bar, line, pie, scatter, heatmap, etc."
                },
                "data": {
                    "type": "object",
                    "description": "Data to visualize"
                },
                "title": {
                    "type": "string",
                    "description": "Chart title"
                },
                "style_options": {
                    "type": "object",
                    "description": "Visual styling options"
                }
            },
            required_params=["chart_type"]
        ))

        # Diagram Generator
        self.register_tool(AgentTool(
            name="generate_diagram",
            description="Generate diagram specifications",
            func=self._generate_diagram,
            parameters={
                "diagram_type": {
                    "type": "string",
                    "description": "Type: flowchart, mindmap, sequence, architecture"
                },
                "elements": {
                    "type": "array",
                    "description": "Elements to include in diagram"
                },
                "connections": {
                    "type": "array",
                    "description": "Connections between elements"
                }
            },
            required_params=["diagram_type"]
        ))

        # Image Prompt Generator
        self.register_tool(AgentTool(
            name="generate_image_prompt",
            description="Generate prompts for AI image generators",
            func=self._generate_image_prompt,
            parameters={
                "description": {
                    "type": "string",
                    "description": "Description of desired image"
                },
                "generator": {
                    "type": "string",
                    "description": "Target generator: dalle, midjourney, stable_diffusion",
                    "default": "dalle"
                },
                "style": {
                    "type": "string",
                    "description": "Art style: photorealistic, illustration, 3d, etc."
                },
                "aspect_ratio": {
                    "type": "string",
                    "description": "Aspect ratio: 1:1, 16:9, 4:3, etc.",
                    "default": "1:1"
                }
            },
            required_params=["description"]
        ))

        # Thumbnail Generator
        self.register_tool(AgentTool(
            name="generate_thumbnail",
            description="Generate thumbnail design specifications",
            func=self._generate_thumbnail,
            parameters={
                "title": {
                    "type": "string",
                    "description": "Title/text for thumbnail"
                },
                "platform": {
                    "type": "string",
                    "description": "Platform: youtube, blog, podcast",
                    "default": "youtube"
                },
                "style": {
                    "type": "string",
                    "description": "Visual style"
                }
            },
            required_params=["title"]
        ))

    def _initialize_prompts(self) -> None:
        """Initialize prompt templates."""

        self.register_prompt_template(
            "infographic_design",
            """Design an infographic with the following specifications:

Topic: {topic}
Purpose: {purpose}
Target Audience: {audience}

Data Points to Include:
{data_points}

Style Guidelines:
- Color Scheme: {color_scheme}
- Visual Style: {style}
- Dimensions: {dimensions}

Generate:
1. Layout structure (sections and hierarchy)
2. Visual elements for each section
3. Icon suggestions
4. Typography recommendations
5. Color palette specifics"""
        )

        self.register_prompt_template(
            "image_prompt_dalle",
            """Create a DALL-E prompt for:

Description: {description}
Style: {style}
Mood: {mood}

Requirements:
- Aspect Ratio: {aspect_ratio}
- Quality: High detail
- Lighting: {lighting}

Generate a detailed, specific prompt optimized for DALL-E 3."""
        )

        self.register_prompt_template(
            "image_prompt_midjourney",
            """Create a Midjourney prompt for:

Description: {description}
Style: {style}
Mood: {mood}

Include appropriate Midjourney parameters:
--ar {aspect_ratio}
--stylize {stylize_value}
--quality {quality}

Generate an evocative prompt with style modifiers."""
        )

    async def _generate_infographic(
        self,
        topic: str,
        data_points: Optional[List[str]] = None,
        style: str = "modern",
        dimensions: Optional[Dict[str, int]] = None
    ) -> Dict[str, Any]:
        """Generate infographic specifications."""
        logger.info(f"Generating infographic for: {topic}")

        data_points = data_points or []
        dimensions = dimensions or {"width": 800, "height": 2000}

        return {
            "type": "infographic",
            "topic": topic,
            "style": style,
            "dimensions": dimensions,
            "layout": {
                "header": {
                    "height": "15%",
                    "elements": ["title", "subtitle", "brand_logo"]
                },
                "body": {
                    "height": "70%",
                    "sections": [
                        {
                            "name": "Introduction",
                            "type": "text_with_icon",
                            "height": "15%"
                        },
                        {
                            "name": "Key Statistics",
                            "type": "data_visualization",
                            "height": "25%"
                        },
                        {
                            "name": "Main Points",
                            "type": "icon_grid",
                            "height": "30%"
                        }
                    ]
                },
                "footer": {
                    "height": "15%",
                    "elements": ["sources", "cta", "branding"]
                }
            },
            "data_points": data_points,
            "color_recommendations": {
                "primary": "#2563EB",
                "secondary": "#3B82F6",
                "accent": "#F59E0B",
                "background": "#F8FAFC",
                "text": "#1E293B"
            },
            "typography": {
                "title": {"font": "Bold Sans", "size": "32px"},
                "heading": {"font": "Semi-Bold Sans", "size": "24px"},
                "body": {"font": "Regular Sans", "size": "14px"}
            },
            "icon_suggestions": [
                "chart-bar", "lightbulb", "target", "users", "trending-up"
            ],
            "status": "specifications_generated"
        }

    async def _describe_chart(
        self,
        chart_type: str,
        data: Optional[Dict[str, Any]] = None,
        title: str = "",
        style_options: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Generate chart description and specifications."""
        logger.info(f"Describing {chart_type} chart")

        data = data or {}
        style_options = style_options or {}

        chart_configs = {
            "bar": {
                "orientation": "vertical",
                "grouping": "grouped",
                "bar_width": 0.8
            },
            "line": {
                "line_style": "smooth",
                "markers": True,
                "area_fill": False
            },
            "pie": {
                "inner_radius": 0,
                "label_position": "outside",
                "explode": None
            },
            "scatter": {
                "marker_size": 10,
                "trend_line": False,
                "color_by": None
            }
        }

        return {
            "chart_type": chart_type,
            "title": title,
            "data": data,
            "configuration": chart_configs.get(chart_type, {}),
            "style": {
                "colors": style_options.get("colors", ["#3B82F6", "#10B981", "#F59E0B"]),
                "font_family": style_options.get("font", "Inter"),
                "grid_lines": style_options.get("grid", True),
                "legend_position": style_options.get("legend", "bottom")
            },
            "accessibility": {
                "alt_text": f"{chart_type} chart showing {title}",
                "data_table": True
            },
            "export_formats": ["svg", "png", "pdf"],
            "status": "description_generated"
        }

    async def _generate_diagram(
        self,
        diagram_type: str,
        elements: Optional[List[str]] = None,
        connections: Optional[List[Dict[str, str]]] = None
    ) -> Dict[str, Any]:
        """Generate diagram specifications."""
        logger.info(f"Generating {diagram_type} diagram")

        elements = elements or []
        connections = connections or []

        diagram_templates = {
            "flowchart": {
                "shapes": {
                    "start_end": "oval",
                    "process": "rectangle",
                    "decision": "diamond",
                    "data": "parallelogram"
                },
                "connectors": ["arrow", "line"],
                "layout": "top-to-bottom"
            },
            "mindmap": {
                "shapes": {
                    "central": "rounded_rectangle",
                    "branch": "rectangle",
                    "leaf": "oval"
                },
                "connectors": ["curved_line"],
                "layout": "radial"
            },
            "sequence": {
                "shapes": {
                    "actor": "stick_figure",
                    "object": "rectangle",
                    "activation": "narrow_rectangle"
                },
                "connectors": ["solid_arrow", "dashed_arrow"],
                "layout": "left-to-right"
            },
            "architecture": {
                "shapes": {
                    "component": "rectangle",
                    "database": "cylinder",
                    "cloud": "cloud",
                    "user": "stick_figure"
                },
                "connectors": ["arrow", "bidirectional_arrow"],
                "layout": "hierarchical"
            }
        }

        template = diagram_templates.get(diagram_type, diagram_templates["flowchart"])

        return {
            "diagram_type": diagram_type,
            "template": template,
            "elements": [
                {
                    "id": f"elem_{i}",
                    "label": elem,
                    "shape": list(template["shapes"].values())[i % len(template["shapes"])]
                }
                for i, elem in enumerate(elements)
            ],
            "connections": connections,
            "style": {
                "line_color": "#64748B",
                "fill_colors": ["#EFF6FF", "#F0FDF4", "#FEF3C7"],
                "border_color": "#334155",
                "font": "Inter"
            },
            "mermaid_code": self._generate_mermaid(diagram_type, elements, connections),
            "status": "specifications_generated"
        }

    def _generate_mermaid(
        self,
        diagram_type: str,
        elements: List[str],
        connections: List[Dict[str, str]]
    ) -> str:
        """Generate Mermaid.js code for diagram."""
        if diagram_type == "flowchart":
            lines = ["flowchart TD"]
            for i, elem in enumerate(elements):
                lines.append(f"    {chr(65+i)}[{elem}]")
            for conn in connections:
                lines.append(f"    {conn.get('from', 'A')} --> {conn.get('to', 'B')}")
            return "\n".join(lines)

        elif diagram_type == "mindmap":
            lines = ["mindmap"]
            if elements:
                lines.append(f"  root(({elements[0]}))")
                for elem in elements[1:]:
                    lines.append(f"    {elem}")
            return "\n".join(lines)

        return f"graph TD\n    A[{elements[0] if elements else 'Start'}]"

    async def _generate_image_prompt(
        self,
        description: str,
        generator: str = "dalle",
        style: str = "photorealistic",
        aspect_ratio: str = "1:1"
    ) -> Dict[str, Any]:
        """Generate optimized prompts for AI image generators."""
        logger.info(f"Generating {generator} prompt for: {description}")

        # Style modifiers by generator
        style_modifiers = {
            "dalle": {
                "photorealistic": "photorealistic, high detail, professional photography",
                "illustration": "digital illustration, vibrant colors, detailed artwork",
                "3d": "3D render, octane render, detailed textures, studio lighting",
                "minimal": "minimalist design, clean lines, simple composition",
                "artistic": "artistic interpretation, expressive brushstrokes, creative"
            },
            "midjourney": {
                "photorealistic": "--v 6 --style raw",
                "illustration": "--niji 6",
                "3d": "--v 6 --style raw --stylize 250",
                "minimal": "--v 6 --stylize 50",
                "artistic": "--v 6 --stylize 750"
            },
            "stable_diffusion": {
                "photorealistic": "(photorealistic:1.4), detailed, 8k uhd",
                "illustration": "digital art, trending on artstation",
                "3d": "3d render, blender, octane",
                "minimal": "minimalist, simple, clean",
                "artistic": "artistic, painterly, expressive"
            }
        }

        prompts = {}

        if generator in ["dalle", "all"]:
            dalle_style = style_modifiers["dalle"].get(style, style_modifiers["dalle"]["photorealistic"])
            prompts["dalle"] = {
                "prompt": f"{description}, {dalle_style}",
                "size": self._get_dalle_size(aspect_ratio),
                "quality": "hd",
                "style": "vivid"
            }

        if generator in ["midjourney", "all"]:
            mj_params = style_modifiers["midjourney"].get(style, style_modifiers["midjourney"]["photorealistic"])
            ar_param = f"--ar {aspect_ratio.replace(':', ':')}"
            prompts["midjourney"] = {
                "prompt": f"{description} {ar_param} {mj_params}",
                "version": "v6"
            }

        if generator in ["stable_diffusion", "all"]:
            sd_style = style_modifiers["stable_diffusion"].get(style, style_modifiers["stable_diffusion"]["photorealistic"])
            prompts["stable_diffusion"] = {
                "prompt": f"{description}, {sd_style}",
                "negative_prompt": "blurry, low quality, distorted, deformed",
                "steps": 30,
                "cfg_scale": 7.5,
                "size": self._get_sd_size(aspect_ratio)
            }

        return {
            "description": description,
            "target_generator": generator,
            "style": style,
            "aspect_ratio": aspect_ratio,
            "prompts": prompts,
            "tips": [
                "Be specific about lighting and composition",
                "Mention the desired mood or atmosphere",
                "Include relevant style references",
                "Specify what to exclude if needed"
            ],
            "status": "prompts_generated"
        }

    def _get_dalle_size(self, aspect_ratio: str) -> str:
        """Convert aspect ratio to DALL-E size."""
        sizes = {
            "1:1": "1024x1024",
            "16:9": "1792x1024",
            "9:16": "1024x1792",
            "4:3": "1024x1024",
            "3:4": "1024x1024"
        }
        return sizes.get(aspect_ratio, "1024x1024")

    def _get_sd_size(self, aspect_ratio: str) -> Dict[str, int]:
        """Convert aspect ratio to Stable Diffusion dimensions."""
        sizes = {
            "1:1": {"width": 1024, "height": 1024},
            "16:9": {"width": 1344, "height": 768},
            "9:16": {"width": 768, "height": 1344},
            "4:3": {"width": 1152, "height": 896},
            "3:4": {"width": 896, "height": 1152}
        }
        return sizes.get(aspect_ratio, {"width": 1024, "height": 1024})

    async def _generate_thumbnail(
        self,
        title: str,
        platform: str = "youtube",
        style: str = "bold"
    ) -> Dict[str, Any]:
        """Generate thumbnail design specifications."""
        logger.info(f"Generating {platform} thumbnail for: {title}")

        platform_specs = {
            "youtube": {
                "dimensions": {"width": 1280, "height": 720},
                "aspect_ratio": "16:9",
                "max_text_area": "40%",
                "safe_zones": {
                    "bottom_right": "timestamp",
                    "bottom_left": "duration"
                }
            },
            "blog": {
                "dimensions": {"width": 1200, "height": 630},
                "aspect_ratio": "1.91:1",
                "max_text_area": "50%"
            },
            "podcast": {
                "dimensions": {"width": 3000, "height": 3000},
                "aspect_ratio": "1:1",
                "max_text_area": "30%"
            }
        }

        specs = platform_specs.get(platform, platform_specs["youtube"])

        return {
            "platform": platform,
            "title": title,
            "specifications": specs,
            "design": {
                "layout": "text_overlay" if style == "bold" else "split",
                "text_position": "left" if style == "bold" else "bottom",
                "text_style": {
                    "font": "Bold Sans",
                    "size": "large",
                    "color": "#FFFFFF",
                    "outline": True,
                    "shadow": True
                },
                "background": {
                    "type": "gradient" if style == "bold" else "solid",
                    "colors": ["#1E40AF", "#7C3AED"]
                }
            },
            "image_prompt": await self._generate_image_prompt(
                f"Thumbnail background for video about {title}, {style} style, eye-catching",
                "dalle",
                "photorealistic",
                specs["aspect_ratio"]
            ),
            "best_practices": [
                "Use contrasting colors for text visibility",
                "Include a face or person when relevant",
                "Keep text to 3-5 words maximum",
                "Use bright, saturated colors",
                "Create visual hierarchy"
            ],
            "status": "specifications_generated"
        }

    async def _process(
        self,
        task: str,
        content: str,
        context: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Process graphics task."""
        self._last_tools_used = []

        visual_type = context.get("type", "infographic")

        result = {
            "task": task,
            "visual_type": visual_type,
            "timestamp": datetime.utcnow().isoformat()
        }

        if visual_type == "infographic":
            self._last_tools_used.append("generate_infographic")
            result["output"] = await self._generate_infographic(
                topic=content,
                data_points=context.get("data_points", []),
                style=context.get("style", "modern")
            )

        elif visual_type in ["chart", "graph"]:
            self._last_tools_used.append("describe_chart")
            result["output"] = await self._describe_chart(
                chart_type=context.get("chart_type", "bar"),
                data=context.get("data", {}),
                title=content
            )

        elif visual_type == "diagram":
            self._last_tools_used.append("generate_diagram")
            result["output"] = await self._generate_diagram(
                diagram_type=context.get("diagram_type", "flowchart"),
                elements=context.get("elements", []),
                connections=context.get("connections", [])
            )

        elif visual_type in ["image", "illustration"]:
            self._last_tools_used.append("generate_image_prompt")
            result["output"] = await self._generate_image_prompt(
                description=content,
                generator=context.get("generator", "dalle"),
                style=context.get("style", "photorealistic"),
                aspect_ratio=context.get("aspect_ratio", "1:1")
            )

        elif visual_type == "thumbnail":
            self._last_tools_used.append("generate_thumbnail")
            result["output"] = await self._generate_thumbnail(
                title=content,
                platform=context.get("platform", "youtube"),
                style=context.get("style", "bold")
            )

        else:
            # Default to image prompt generation
            self._last_tools_used.append("generate_image_prompt")
            result["output"] = await self._generate_image_prompt(
                description=content,
                generator="dalle"
            )

        return result
