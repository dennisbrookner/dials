/*
 * fonts_2d.h
 *
 *  Copyright (C) 2015 Diamond Light Source
 *
 *  Author: Luis Fuentes-Montero (Luiso)
 *
 *  This code is distributed under the BSD license, a copy of which is
 *  included in the root directory of this package.
 */

#ifndef DIALS_FONTS_LOW_LEVEL_H
#define DIALS_FONTS_LOW_LEVEL_H
#include <iostream>
#include <string>
#include <cmath>
#include <scitbx/array_family/flex_types.h>

using scitbx::af::flex_double;
using scitbx::af::flex_grid;
using scitbx::af::flex_int;

int get_font_img_array(int (&font_bw_img)[14][7][16]) {
  int err_cod = 0;

  int arr_2d_0[14][7] = {{0, 0, 0, 0, 0, 0, 0},
                         {0, 0, 1, 1, 1, 1, 0},
                         {0, 1, 1, 1, 1, 1, 1},
                         {0, 1, 1, 0, 0, 1, 1},
                         {0, 1, 0, 0, 0, 1, 1},
                         {0, 1, 0, 0, 1, 0, 1},
                         {0, 1, 0, 0, 1, 0, 1},
                         {0, 1, 0, 1, 1, 0, 1},
                         {0, 1, 0, 1, 0, 0, 1},
                         {0, 1, 0, 1, 0, 0, 1},
                         {0, 1, 1, 0, 0, 1, 1},
                         {0, 1, 1, 1, 1, 1, 1},
                         {0, 0, 1, 1, 1, 1, 0},
                         {0, 0, 0, 0, 0, 0, 0}};
  for (int col = 0; col < 7; col++) {
    for (int row = 0; row < 14; row++) {
      font_bw_img[row][col][0] = arr_2d_0[row][col];
    }
  }

  int arr_2d_1[14][7] = {{0, 0, 0, 0, 0, 0, 0},
                         {0, 1, 1, 1, 0, 0, 0},
                         {0, 1, 1, 1, 0, 0, 0},
                         {0, 0, 0, 1, 0, 0, 0},
                         {0, 0, 0, 1, 0, 0, 0},
                         {0, 0, 0, 1, 0, 0, 0},
                         {0, 0, 0, 1, 0, 0, 0},
                         {0, 0, 0, 1, 0, 0, 0},
                         {0, 0, 0, 1, 0, 0, 0},
                         {0, 0, 0, 1, 0, 0, 0},
                         {0, 0, 0, 1, 0, 0, 0},
                         {0, 1, 1, 1, 1, 1, 0},
                         {0, 1, 1, 1, 1, 1, 0},
                         {0, 0, 0, 0, 0, 0, 0}};
  for (int col = 0; col < 7; col++) {
    for (int row = 0; row < 14; row++) {
      font_bw_img[row][col][1] = arr_2d_1[row][col];
    }
  }

  int arr_2d_2[14][7] = {{0, 0, 0, 0, 0, 0, 0},
                         {0, 0, 0, 1, 1, 0, 0},
                         {0, 0, 1, 1, 1, 1, 0},
                         {0, 1, 1, 0, 0, 1, 1},
                         {0, 1, 0, 0, 0, 1, 1},
                         {0, 0, 0, 0, 0, 1, 1},
                         {0, 0, 0, 0, 1, 1, 0},
                         {0, 0, 0, 0, 1, 1, 0},
                         {0, 0, 0, 1, 1, 0, 0},
                         {0, 0, 0, 1, 1, 0, 0},
                         {0, 0, 1, 1, 0, 0, 0},
                         {0, 0, 1, 1, 1, 1, 1},
                         {0, 1, 1, 1, 1, 1, 1},
                         {0, 0, 0, 0, 0, 0, 0}};
  for (int col = 0; col < 7; col++) {
    for (int row = 0; row < 14; row++) {
      font_bw_img[row][col][2] = arr_2d_2[row][col];
    }
  }

  int arr_2d_3[14][7] = {{0, 0, 0, 0, 0, 0, 0},
                         {0, 0, 0, 1, 1, 0, 0},
                         {0, 0, 1, 1, 1, 1, 0},
                         {0, 1, 1, 0, 0, 1, 1},
                         {0, 1, 0, 0, 0, 1, 1},
                         {0, 0, 0, 0, 0, 1, 1},
                         {0, 0, 0, 0, 1, 1, 0},
                         {0, 0, 0, 1, 1, 1, 0},
                         {0, 0, 0, 0, 0, 1, 1},
                         {0, 0, 0, 0, 0, 1, 1},
                         {0, 1, 0, 0, 0, 1, 1},
                         {0, 1, 1, 1, 1, 1, 0},
                         {0, 0, 1, 1, 1, 0, 0},
                         {0, 0, 0, 0, 0, 0, 0}};
  for (int col = 0; col < 7; col++) {
    for (int row = 0; row < 14; row++) {
      font_bw_img[row][col][3] = arr_2d_3[row][col];
    }
  }

  int arr_2d_4[14][7] = {{0, 0, 0, 0, 0, 0, 0},
                         {0, 0, 0, 0, 0, 1, 0},
                         {0, 0, 0, 0, 1, 1, 0},
                         {0, 0, 0, 0, 1, 1, 0},
                         {0, 0, 0, 1, 1, 1, 0},
                         {0, 0, 0, 1, 0, 1, 0},
                         {0, 0, 1, 1, 0, 1, 0},
                         {0, 0, 1, 0, 0, 1, 0},
                         {0, 1, 1, 0, 0, 1, 0},
                         {0, 1, 1, 1, 1, 1, 1},
                         {0, 0, 0, 0, 0, 1, 0},
                         {0, 0, 0, 0, 0, 1, 0},
                         {0, 0, 0, 0, 0, 1, 0},
                         {0, 0, 0, 0, 0, 0, 0}};
  for (int col = 0; col < 7; col++) {
    for (int row = 0; row < 14; row++) {
      font_bw_img[row][col][4] = arr_2d_4[row][col];
    }
  }

  int arr_2d_5[14][7] = {{0, 0, 0, 0, 0, 0, 0},
                         {0, 1, 1, 1, 1, 1, 0},
                         {0, 1, 1, 1, 1, 1, 0},
                         {0, 1, 0, 0, 0, 0, 0},
                         {0, 1, 0, 0, 0, 0, 0},
                         {0, 1, 0, 0, 0, 0, 0},
                         {0, 1, 1, 1, 1, 1, 0},
                         {0, 1, 1, 1, 1, 1, 1},
                         {0, 0, 0, 0, 0, 1, 1},
                         {0, 0, 0, 0, 0, 0, 1},
                         {0, 1, 1, 0, 0, 0, 1},
                         {0, 1, 1, 1, 1, 1, 1},
                         {0, 0, 1, 1, 1, 1, 0},
                         {0, 0, 0, 0, 0, 0, 0}};
  for (int col = 0; col < 7; col++) {
    for (int row = 0; row < 14; row++) {
      font_bw_img[row][col][5] = arr_2d_5[row][col];
    }
  }

  int arr_2d_6[14][7] = {{0, 0, 0, 0, 0, 0, 0},
                         {0, 0, 0, 1, 1, 0, 0},
                         {0, 0, 1, 1, 1, 1, 0},
                         {0, 1, 1, 0, 0, 1, 1},
                         {0, 1, 1, 0, 0, 0, 0},
                         {0, 1, 1, 0, 0, 0, 0},
                         {0, 1, 1, 1, 1, 1, 0},
                         {0, 1, 1, 1, 1, 1, 1},
                         {0, 1, 1, 0, 0, 1, 1},
                         {0, 1, 1, 0, 0, 0, 1},
                         {0, 1, 1, 0, 0, 0, 1},
                         {0, 1, 1, 1, 1, 1, 1},
                         {0, 0, 1, 1, 1, 1, 0},
                         {0, 0, 0, 0, 0, 0, 0}};
  for (int col = 0; col < 7; col++) {
    for (int row = 0; row < 14; row++) {
      font_bw_img[row][col][6] = arr_2d_6[row][col];
    }
  }

  int arr_2d_7[14][7] = {{0, 0, 0, 0, 0, 0, 0},
                         {0, 1, 1, 1, 1, 1, 1},
                         {0, 1, 1, 1, 1, 1, 1},
                         {0, 0, 0, 0, 0, 1, 1},
                         {0, 0, 0, 0, 0, 1, 1},
                         {0, 0, 0, 0, 0, 1, 1},
                         {0, 0, 0, 0, 1, 1, 0},
                         {0, 0, 0, 0, 1, 1, 0},
                         {0, 0, 0, 1, 1, 0, 0},
                         {0, 0, 0, 1, 1, 0, 0},
                         {0, 0, 1, 1, 0, 0, 0},
                         {0, 0, 1, 1, 0, 0, 0},
                         {0, 1, 1, 0, 0, 0, 0},
                         {0, 0, 0, 0, 0, 0, 0}};
  for (int col = 0; col < 7; col++) {
    for (int row = 0; row < 14; row++) {
      font_bw_img[row][col][7] = arr_2d_7[row][col];
    }
  }

  int arr_2d_8[14][7] = {{0, 0, 0, 0, 0, 0, 0},
                         {0, 0, 0, 1, 1, 0, 0},
                         {0, 0, 1, 1, 1, 1, 0},
                         {0, 1, 1, 0, 0, 1, 1},
                         {0, 1, 1, 0, 0, 1, 1},
                         {0, 1, 1, 0, 0, 1, 1},
                         {0, 0, 1, 1, 1, 1, 0},
                         {0, 0, 1, 1, 1, 1, 0},
                         {0, 1, 1, 0, 0, 1, 1},
                         {0, 1, 1, 0, 0, 1, 1},
                         {0, 1, 1, 0, 0, 1, 1},
                         {0, 0, 1, 1, 1, 1, 0},
                         {0, 0, 0, 1, 1, 0, 0},
                         {0, 0, 0, 0, 0, 0, 0}};
  for (int col = 0; col < 7; col++) {
    for (int row = 0; row < 14; row++) {
      font_bw_img[row][col][8] = arr_2d_8[row][col];
    }
  }

  int arr_2d_9[14][7] = {{0, 0, 0, 0, 0, 0, 0},
                         {0, 0, 0, 1, 1, 0, 0},
                         {0, 0, 1, 1, 1, 1, 0},
                         {0, 1, 1, 0, 0, 1, 1},
                         {0, 1, 1, 0, 0, 1, 1},
                         {0, 1, 1, 0, 0, 1, 1},
                         {0, 1, 1, 1, 1, 1, 1},
                         {0, 0, 1, 1, 1, 1, 1},
                         {0, 0, 0, 0, 0, 1, 1},
                         {0, 0, 0, 0, 0, 1, 1},
                         {0, 0, 0, 0, 1, 1, 0},
                         {0, 1, 1, 1, 1, 1, 0},
                         {0, 0, 1, 1, 1, 0, 0},
                         {0, 0, 0, 0, 0, 0, 0}};
  for (int col = 0; col < 7; col++) {
    for (int row = 0; row < 14; row++) {
      font_bw_img[row][col][9] = arr_2d_9[row][col];
    }
  }

  int arr_2d_point[14][7] = {{0, 0, 0, 0, 0, 0, 0},
                             {0, 0, 0, 0, 0, 0, 0},
                             {0, 0, 0, 0, 0, 0, 0},
                             {0, 0, 0, 0, 0, 0, 0},
                             {0, 0, 0, 0, 0, 0, 0},
                             {0, 0, 0, 0, 0, 0, 0},
                             {0, 0, 0, 0, 0, 0, 0},
                             {0, 0, 0, 0, 0, 0, 0},
                             {0, 0, 0, 0, 0, 0, 0},
                             {0, 0, 0, 1, 1, 0, 0},
                             {0, 0, 0, 1, 1, 0, 0},
                             {0, 0, 0, 1, 1, 0, 0},
                             {0, 0, 0, 0, 0, 0, 0},
                             {0, 0, 0, 0, 0, 0, 0}};
  for (int col = 0; col < 7; col++) {
    for (int row = 0; row < 14; row++) {
      font_bw_img[row][col][10] = arr_2d_point[row][col];
    }
  }

  int arr_2d_e[14][7] = {{0, 0, 0, 0, 0, 0, 0},
                         {0, 0, 0, 0, 0, 0, 0},
                         {0, 0, 1, 1, 1, 1, 0},
                         {0, 1, 1, 1, 1, 1, 1},
                         {0, 1, 1, 0, 0, 1, 1},
                         {0, 1, 1, 0, 0, 1, 1},
                         {0, 1, 1, 1, 1, 1, 1},
                         {0, 1, 1, 1, 1, 1, 0},
                         {0, 1, 1, 0, 0, 0, 0},
                         {0, 1, 1, 0, 0, 0, 0},
                         {0, 1, 1, 1, 0, 1, 1},
                         {0, 0, 1, 1, 1, 1, 0},
                         {0, 0, 0, 1, 1, 0, 0},
                         {0, 0, 0, 0, 0, 0, 0}};
  for (int col = 0; col < 7; col++) {
    for (int row = 0; row < 14; row++) {
      font_bw_img[row][col][11] = arr_2d_e[row][col];
    }
  }

  int arr_2d_plus[14][7] = {{0, 0, 0, 0, 0, 0, 0},
                            {0, 0, 0, 1, 0, 0, 0},
                            {0, 0, 0, 1, 0, 0, 0},
                            {0, 0, 0, 1, 0, 0, 0},
                            {0, 0, 0, 1, 0, 0, 0},
                            {0, 0, 0, 1, 0, 0, 0},
                            {0, 1, 1, 1, 1, 1, 0},
                            {0, 1, 1, 1, 1, 1, 0},
                            {0, 0, 0, 1, 0, 0, 0},
                            {0, 0, 0, 1, 0, 0, 0},
                            {0, 0, 0, 1, 0, 0, 0},
                            {0, 0, 0, 1, 0, 0, 0},
                            {0, 0, 0, 1, 0, 0, 0},
                            {0, 0, 0, 0, 0, 0, 0}};
  for (int col = 0; col < 7; col++) {
    for (int row = 0; row < 14; row++) {
      font_bw_img[row][col][12] = arr_2d_plus[row][col];
    }
  }

  int arr_2d_minus[14][7] = {{0, 0, 0, 0, 0, 0, 0},
                             {0, 0, 0, 0, 0, 0, 0},
                             {0, 0, 0, 0, 0, 0, 0},
                             {0, 0, 0, 0, 0, 0, 0},
                             {0, 0, 0, 0, 0, 0, 0},
                             {0, 0, 0, 0, 0, 0, 0},
                             {0, 1, 1, 1, 1, 1, 0},
                             {0, 1, 1, 1, 1, 1, 0},
                             {0, 0, 0, 0, 0, 0, 0},
                             {0, 0, 0, 0, 0, 0, 0},
                             {0, 0, 0, 0, 0, 0, 0},
                             {0, 0, 0, 0, 0, 0, 0},
                             {0, 0, 0, 0, 0, 0, 0},
                             {0, 0, 0, 0, 0, 0, 0}};
  for (int col = 0; col < 7; col++) {
    for (int row = 0; row < 14; row++) {
      font_bw_img[row][col][13] = arr_2d_minus[row][col];
    }
  }

  int arr_2d_space[14][7] = {{0, 0, 0, 0, 0, 0, 0},
                             {0, 0, 0, 0, 0, 0, 0},
                             {0, 0, 0, 0, 0, 0, 0},
                             {0, 0, 0, 0, 0, 0, 0},
                             {0, 0, 0, 0, 0, 0, 0},
                             {0, 0, 0, 0, 0, 0, 0},
                             {0, 0, 0, 0, 0, 0, 0},
                             {0, 0, 0, 0, 0, 0, 0},
                             {0, 0, 0, 0, 0, 0, 0},
                             {0, 0, 0, 0, 0, 0, 0},
                             {0, 0, 0, 0, 0, 0, 0},
                             {0, 0, 0, 0, 0, 0, 0},
                             {0, 0, 0, 0, 0, 0, 0},
                             {0, 0, 0, 0, 0, 0, 0}};
  for (int col = 0; col < 7; col++) {
    for (int row = 0; row < 14; row++) {
      font_bw_img[row][col][14] = arr_2d_space[row][col];
    }
  }

  int arr_2d_null[14][7] = {{0, 0, 0, 0, 0, 0, 0},
                            {0, 0, 0, 0, 0, 0, 0},
                            {0, 0, 0, 0, 0, 0, 0},
                            {0, 0, 0, 0, 0, 0, 0},
                            {0, 0, 0, 0, 0, 0, 0},
                            {0, 0, 0, 0, 0, 0, 0},
                            {0, 0, 0, 0, 0, 0, 0},
                            {0, 0, 0, 0, 0, 0, 0},
                            {0, 0, 0, 0, 0, 0, 0},
                            {0, 0, 0, 0, 0, 0, 0},
                            {0, 0, 0, 0, 0, 0, 0},
                            {0, 0, 0, 0, 0, 0, 0},
                            {0, 0, 0, 0, 0, 0, 0},
                            {0, 0, 0, 0, 0, 0, 0}};
  for (int col = 0; col < 7; col++) {
    for (int row = 0; row < 14; row++) {
      font_bw_img[row][col][15] = arr_2d_null[row][col];
    }
  }

  return err_cod;
}

int get_digits(double nm, int (&dgt_num)[15]) {
  int err_cod = 0;
  bool end_reached;

  char asc_str[15];

  std::string str;
  snprintf(asc_str, 15, "               ");
  snprintf(asc_str, 15, "%g", nm);

  // std::cout << "asc_str = <<" << asc_str << ">>\n\n";
  str = asc_str;
  end_reached = false;
  for (int i = 0; i < 13; i++) {
    str = asc_str[i];
    dgt_num[i] = asc_str[i] - 48;

    if (dgt_num[i] < 0 || dgt_num[i] > 9) {
      if (str == ".") {
        dgt_num[i] = 10;
      } else if (str == "e") {
        dgt_num[i] = 11;
      } else if (str == "+") {
        dgt_num[i] = 12;
      } else if (str == "-") {
        dgt_num[i] = 13;
      } else if (str == " ") {
        dgt_num[i] = 14;
      } else if (asc_str[i] == 0) {
        dgt_num[i] = 15;
        end_reached = true;
      } else {
        if (end_reached == false) {
          // std::cout << "\nfound \'" << str << "\' and not converted";
          err_cod = asc_str[i];
          // std::cout << "\n char(" << err_cod << ") found\n";
          err_cod = 1;
        }
      }
    }
    // std::cout << " {" << asc_str[i] << "} " << "["<< dgt_num[i] <<"],";
  }

  if (end_reached == false) {
    // std::cout << "\n to long number, err 2 \n";
    err_cod = 2;
  }
  // std::cout << "\nerr_cod =" << err_cod << "\n";

  return err_cod;
}

#endif
