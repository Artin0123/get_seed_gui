#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "finders.h"

// 結構體
typedef struct {
  uint64_t seed;
  double x_coord;  // 改為 double
  double z_coord;  // 改為 double
  char world_type[20];
} WorldInfo;

// 計算距離
double calculate_distance(int x1, int z1, int x2, int z2) {
  return sqrt(pow(x2 - x1, 2) + pow(z2 - z1, 2));
}

// 讀取函數
WorldInfo read_world_info(const char* filename) {
  WorldInfo info;
  FILE* file = fopen(filename, "r");
  if (file == NULL) {
    fprintf(stderr, "cannot open: %s\n", filename);
    exit(1);
  }

  // 計算行數
  int line_count = 0;
  char line[256];
  while (fgets(line, sizeof(line), file) != NULL) {
    line_count++;
  }
  rewind(file);

  // 讀取 seed
  if (fgets(line, sizeof(line), file) == NULL ||
      sscanf(line, "%" SCNu64, &info.seed) != 1) {
    fprintf(stderr, "error reading seed\n");
    fclose(file);
    exit(1);
  }

  if (line_count < 4) {
    // 初始化生成器取得 spawn
    Generator g;
    setupGenerator(&g, MC_1_16_1, 0);
    applySeed(&g, DIM_OVERWORLD, info.seed);
    Pos spawn = getSpawn(&g);

    fclose(file);
    file = fopen(filename, "w");
    fprintf(file, "%" PRId64 "\n%d\n%d\noverworld\n", info.seed, spawn.x,
            spawn.z);

    info.x_coord = spawn.x;
    info.z_coord = spawn.z;
    strcpy(info.world_type, "overworld");
  } else {
    // 讀取 x 座標
    if (fgets(line, sizeof(line), file) == NULL ||
        sscanf(line, "%lf", &info.x_coord) != 1) {
      fprintf(stderr, "error reading x coordinate\n");
      fclose(file);
      exit(1);
    }

    // 讀取 z 座標
    if (fgets(line, sizeof(line), file) == NULL ||
        sscanf(line, "%lf", &info.z_coord) != 1) {
      fprintf(stderr, "error reading z coordinate\n");
      fclose(file);
      exit(1);
    }

    // 讀取維度類型
    if (fgets(line, sizeof(line), file) == NULL ||
        sscanf(line, "%s", info.world_type) != 1) {
      fprintf(stderr, "error reading world type\n");
      fclose(file);
      exit(1);
    }
  }

  fclose(file);
  return info;
}

int main() {
  int mc = MC_1_16_1;
  const char* filename = "world_info.txt";

  // 讀取所有資料
  WorldInfo info = read_world_info(filename);

  // 如果是終界則直接結束
  if (strcmp(info.world_type, "the_end") == 0) {
    return 0;
  }

  // 如果是地獄則座標乘以8
  int x = info.x_coord;
  int z = info.z_coord;
  if (strcmp(info.world_type, "the_nether") == 0) {
    x *= 8;
    z *= 8;
  }

  StrongholdIter sh;
  Generator g;
  setupGenerator(&g, mc, 0);
  applySeed(&g, DIM_OVERWORLD, info.seed);

  // 計算搜索範圍（以區塊為單位，16格=1區塊）
  int chunk_radius = 96 / 16;  // 轉換格數為區塊數

  // 遍歷範圍內的所有區塊
  if (strcmp(info.world_type, "overworld") == 0) {
    for (int chunk_x = -chunk_radius; chunk_x <= chunk_radius; chunk_x++) {
      for (int chunk_z = -chunk_radius; chunk_z <= chunk_radius; chunk_z++) {
        // 計算當前區塊的實際座標 (使用 info.x_coord 和 info.z_coord)
        int current_x = x / 16 + chunk_x;
        int current_z = z / 16 + chunk_z;

        Pos p;
        if (getStructurePos(Treasure, mc, info.seed & 0xFFFFFFFFFFFF, current_x,
                            current_z, &p)) {
          // 檢查座標是否在玩家位置96格範圍內
          int rel_x = p.x - x;
          int rel_z = p.z - z;

          if (abs(rel_x) <= 96 && abs(rel_z) <= 96) {
            if (isViableStructurePos(Treasure, &g, p.x, p.z, 0)) {
              double distance = calculate_distance(x, z, p.x, p.z);
              // 計算角度 (atan2 會回傳弧度)
              double angle = atan2(-rel_x, rel_z) * 180.0 / M_PI;
              // 調整角度範圍至 -180 到 180 度
              if (angle < -180) {
                angle += 360;
              }
              if (angle > 180) {
                angle -= 360;
              }
              printf("bt: (%d, %d)\n%.1f (%.2f blocks)\n\n", p.x, p.z, angle,
                     distance);
            }
          }
        }
      }
    }
  }

  // 追蹤最近的要塞
  double min_distance = INFINITY;
  Pos closest_stronghold;
  int stronghold_number = 0;

  // 檢查所有要塞
  initFirstStronghold(&sh, mc, info.seed);
  for (int i = 1; i <= 9; i++) {
    if (nextStronghold(&sh, &g) <= 0)
      break;

    double dist = calculate_distance(x, z, sh.pos.x, sh.pos.z);
    if (dist < min_distance) {
      min_distance = dist;
      closest_stronghold = sh.pos;
      stronghold_number = i;
    }
  }

  // 輸出最近的要塞
  if (strcmp(info.world_type, "the_nether") == 0) {
    int rel_x = (closest_stronghold.x / 8) - (int)info.x_coord;
    int rel_z = (closest_stronghold.z / 8) - (int)info.z_coord;
    double angle = atan2(-rel_x, rel_z) * 180.0 / M_PI;
    if (angle < -180)
      angle += 360;
    if (angle > 180)
      angle -= 360;

    printf("sh #%d: (%d, %d)\n%.1f (%.2f blocks)\n", stronghold_number,
           closest_stronghold.x / 8, closest_stronghold.z / 8, angle,
           min_distance / 8);
  } else {
    int rel_x = closest_stronghold.x - (int)info.x_coord;
    int rel_z = closest_stronghold.z - (int)info.z_coord;
    double angle = atan2(-rel_x, rel_z) * 180.0 / M_PI;
    if (angle < -180) {
      angle += 360;
    }
    if (angle > 180) {
      angle -= 360;
    }
    printf("sh #%d: (%d, %d)\n%.1f (%.2f blocks)\n", stronghold_number,
           closest_stronghold.x, closest_stronghold.z, angle, min_distance);
  }

  return 0;
}