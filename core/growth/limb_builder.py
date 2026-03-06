"""Limb Builder - 肢体容器构建和部署模块

负责将生成的肢体代码构建成 Docker 容器并部署。
"""
from typing import Dict, Any, List, Optional, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import json
import subprocess
import hashlib
from datetime import datetime, timezone

from common.logger import get_logger

logger = get_logger(__name__)


@dataclass
class BuildConfig:
    """构建配置"""
    python_version: str = "3.11"
    base_image: str = "python:3.11-slim"
    registry: Optional[str] = None  # Docker registry 地址
    push_to_registry: bool = False  # 是否推送到 registry


@dataclass
class BuildResult:
    """构建结果"""
    success: bool
    image_name: str
    image_tag: str
    build_time: float  # 秒
    log: List[str] = field(default_factory=list)
    error: Optional[str] = None
    container_id: Optional[str] = None  # 如果已部署


@dataclass
class LimbDeployment:
    """肢体部署信息"""
    limb_name: str
    image_name: str
    container_id: str
    port_mapping: Dict[str, str] = field(default_factory=dict)
    volume_mapping: Dict[str, str] = field(default_factory=dict)
    env_vars: Dict[str, str] = field(default_factory=dict)
    deployed_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    status: str = "running"  # running, stopped, failed


class LimbBuilder:
    """肢体构建器

    负责：
    1. 生成 Dockerfile
    2. 构建 Docker 镜像
    3. 部署容器
    4. 管理容器生命周期
    """

    def __init__(self, config: BuildConfig = None):
        """初始化构建器

        Args:
            config: 构建配置
        """
        self.config = config or BuildConfig()
        self._deployed_limbs: Dict[str, LimbDeployment] = {}

        # 工作目录
        self._build_dir = Path("artifacts/builds")
        self._build_dir.mkdir(parents=True, exist_ok=True)

    def build_limb(
        self,
        limb_name: str,
        code: str,
        requirements: List[str] = None,
        dockerfile_content: str = None
    ) -> BuildResult:
        """构建肢体镜像

        Args:
            limb_name: 肢体名称
            code: 肢体代码
            requirements: Python 依赖列表
            dockerfile_content: 自定义 Dockerfile（可选）

        Returns:
            构建结果
        """
        import time
        start_time = time.time()
        logs = []

        try:
            # 1. 创建构建目录
            limb_build_dir = self._build_dir / limb_name
            limb_build_dir.mkdir(parents=True, exist_ok=True)

            # 2. 写入代码
            code_file = limb_build_dir / "__init__.py"
            with open(code_file, 'w', encoding='utf-8') as f:
                f.write(code)
            logs.append(f"代码已写入: {code_file}")

            # 3. 写入依赖
            if requirements:
                req_file = limb_build_dir / "requirements.txt"
                with open(req_file, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(requirements))
                logs.append(f"依赖已写入: {req_file}")

            # 4. 生成/写入 Dockerfile
            if dockerfile_content:
                dockerfile = dockerfile_content
            else:
                dockerfile = self._generate_dockerfile(requirements or [])

            dockerfile_path = limb_build_dir / "Dockerfile"
            with open(dockerfile_path, 'w', encoding='utf-8') as f:
                f.write(dockerfile)
            logs.append(f"Dockerfile 已生成: {dockerfile_path}")

            # 5. 构建 Docker 镜像
            image_name = f"genesisx/{limb_name}"
            image_tag = self._compute_image_tag(code)

            build_cmd = [
                "docker", "build",
                "-t", f"{image_name}:{image_tag}",
                "-t", f"{image_name}:latest",  # 同时打 latest 标签
                str(limb_build_dir)
            ]

            logs.append(f"执行构建命令: {' '.join(build_cmd)}")

            # 执行构建
            result = subprocess.run(
                build_cmd,
                capture_output=True,
                text=True,
                timeout=300  # 5分钟超时
            )

            if result.returncode != 0:
                logger.error(f"Docker 构建失败: {result.stderr}")
                return BuildResult(
                    success=False,
                    image_name=image_name,
                    image_tag=image_tag,
                    build_time=time.time() - start_time,
                    error=result.stderr
                )

            logs.append("Docker 镜像构建成功")

            build_time = time.time() - start_time
            logger.info(f"肢体 {limb_name} 构建成功，耗时 {build_time:.2f} 秒")

            return BuildResult(
                success=True,
                image_name=image_name,
                image_tag=image_tag,
                build_time=build_time,
                log=logs
            )

        except subprocess.TimeoutExpired:
            error = "Docker 构建超时"
            logger.error(error)
            return BuildResult(
                success=False,
                image_name=f"genesisx/{limb_name}",
                image_tag="unknown",
                build_time=time.time() - start_time,
                error=error
            )
        except Exception as e:
            error = f"构建失败: {e}"
            logger.error(error)
            return BuildResult(
                success=False,
                image_name=f"genesisx/{limb_name}",
                image_tag="unknown",
                build_time=time.time() - start_time,
                error=error
            )

    def _generate_dockerfile(self, requirements: List[str]) -> str:
        """生成 Dockerfile

        Args:
            requirements: Python 依赖列表

        Returns:
            Dockerfile 内容
        """
        base_image = self.config.base_image

        dockerfile = f"""FROM {base_image}

# 设置工作目录
WORKDIR /limb

# 复制依赖文件
COPY requirements.txt .

# 安装依赖
RUN pip install --no-cache-dir -r requirements.txt || true

# 复制代码
COPY __init__.py .

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV LIMB_NAME=/limb

# 默认命令
CMD ["python", "-u", "__init__.py"]
"""
        return dockerfile

    def _compute_image_tag(self, code: str) -> str:
        """计算镜像标签（基于代码哈希）"""
        hash_val = hashlib.md5(code.encode()).hexdigest()[:12]
        return hash_val

    def deploy_limb(
        self,
        image_name: str,
        image_tag: str = "latest",
        port_mapping: Dict[str, str] = None,
        volume_mapping: Dict[str, str] = None,
        env_vars: Dict[str, str] = None,
        detach: bool = True
    ) -> Tuple[bool, Optional[str]]:
        """部署肢体容器

        Args:
            image_name: 镜像名称
            image_tag: 镜像标签
            port_mapping: 端口映射 {"8080": "8080"}
            volume_mapping: 卷映射
            env_vars: 环境变量
            detach: 是否后台运行

        Returns:
            (是否成功, 容器ID 或 错误消息)
        """
        try:
            # 构建 docker run 命令
            cmd = ["docker", "run"]

            if detach:
                cmd.append("-d")

            # 端口映射
            if port_mapping:
                for host_port, container_port in port_mapping.items():
                    cmd.extend(["-p", f"{host_port}:{container_port}"])

            # 卷映射
            if volume_mapping:
                for host_path, container_path in volume_mapping.items():
                    cmd.extend(["-v", f"{host_path}:{container_path}"])

            # 环境变量
            if env_vars:
                for key, value in env_vars.items():
                    cmd.extend(["-e", f"{key}={value}"])

            # 镜像
            full_image = f"{image_name}:{image_tag}"
            cmd.append(full_image)

            # 执行部署
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                error_msg = f"容器启动失败: {result.stderr}"
                logger.error(error_msg)
                return False, error_msg

            container_id = result.stdout.strip()

            logger.info(f"容器已启动: {container_id} ({full_image})")
            return True, container_id

        except subprocess.TimeoutExpired:
            error_msg = "容器启动超时"
            logger.error(error_msg)
            return False, error_msg
        except Exception as e:
            error_msg = f"部署失败: {e}"
            logger.error(error_msg)
            return False, error_msg

    def stop_limb(self, container_id: str) -> bool:
        """停止肢体容器

        Args:
            container_id: 容器ID

        Returns:
            是否成功
        """
        try:
            result = subprocess.run(
                ["docker", "stop", container_id],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                logger.info(f"容器已停止: {container_id}")
                return True
            else:
                logger.warning(f"停止容器失败: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"停止容器异常: {e}")
            return False

    def remove_limb(self, container_id: str, force: bool = True) -> bool:
        """删除肢体容器

        Args:
            container_id: 容器ID
            force: 是否强制删除

        Returns:
            是否成功
        """
        try:
            cmd = ["docker", "rm"]
            if force:
                cmd.append("-f")
            cmd.append(container_id)

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode == 0:
                logger.info(f"容器已删除: {container_id}")
                return True
            else:
                logger.warning(f"删除容器失败: {result.stderr}")
                return False

        except Exception as e:
            logger.error(f"删除容器异常: {e}")
            return False

    def get_container_status(self, container_id: str) -> Optional[str]:
        """获取容器状态

        Args:
            container_id: 容器ID

        Returns:
            状态字符串 (running, exited, etc.) 或 None
        """
        try:
            result = subprocess.run(
                ["docker", "inspect", "-f", "{{.State.Status}}", container_id],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                return result.stdout.strip()
            return None

        except Exception as e:
            logger.error(f"获取容器状态失败: {e}")
            return None

    def list_limbs(self) -> List[str]:
        """列出所有肢体容器

        Returns:
            容器ID列表
        """
        try:
            result = subprocess.run(
                ["docker", "ps", "-q", "--filter", "label=genesisx.limb=true"],
                capture_output=True,
                text=True,
                timeout=10
            )

            if result.returncode == 0:
                return result.stdout.strip().split('\n') if result.stdout.strip() else []
            return []

        except Exception as e:
            logger.error(f"列出容器失败: {e}")
            return []

    def prune_old_images(self, keep_n: int = 3) -> int:
        """清理旧的肢体镜像

        Args:
            keep_n: 保留最近N个镜像

        Returns:
            清理的镜像数量
        """
        try:
            # 获取所有 genesisx/* 镜像
            result = subprocess.run(
                ["docker", "images", "genesisx/*", "--format", "{{.ID}}:{{.CreatedAt}}"],
                capture_output=True,
                text=True,
                timeout=30
            )

            if result.returncode != 0:
                return 0

            # 解析并排序
            images = []
            for line in result.stdout.strip().split('\n'):
                if ':' in line:
                    images.append(line)

            # 保留最新的 N 个，删除其余的
            if len(images) <= keep_n:
                return 0

            to_remove = images[:-keep_n]
            removed_count = 0

            for img_info in to_remove:
                image_id = img_info.split(':')[0]
                rm_result = subprocess.run(
                    ["docker", "rmi", "-f", image_id],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if rm_result.returncode == 0:
                    removed_count += 1

            logger.info(f"清理了 {removed_count} 个旧镜像")
            return removed_count

        except Exception as e:
            logger.error(f"清理镜像失败: {e}")
            return 0


# 便捷函数

def create_limb_builder(config: BuildConfig = None) -> LimbBuilder:
    """创建肢体构建器

    Args:
        config: 构建配置

    Returns:
        LimbBuilder 实例
    """
    return LimbBuilder(config)


def build_and_deploy(
    limb_name: str,
    code: str,
    requirements: List[str] = None,
    config: BuildConfig = None
) -> Tuple[bool, Optional[str]]:
    """一键构建和部署肢体

    Args:
        limb_name: 肢体名称
        code: 肢体代码
        requirements: Python 依赖
        config: 构建配置

    Returns:
        (是否成功, 容器ID 或 错误消息)
    """
    builder = create_limb_builder(config)

    # 构建
    build_result = builder.build_limb(limb_name, code, requirements)
    if not build_result.success:
        return False, build_result.error

    # 部署
    success, container_id = builder.deploy_limb(
        build_result.image_name,
        build_result.image_tag
    )

    return success, container_id
